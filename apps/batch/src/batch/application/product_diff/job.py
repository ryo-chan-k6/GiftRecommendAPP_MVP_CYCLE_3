"""BATCH-006 商品差分判定ジョブ実装.

処理 Phase（仕様書 §8.2）:
plan → load_staging → resolve_item → compare → persist → status → finalize
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from batch.application.job_run import JobRunTracker, ScaffoldJobRunTracker
from batch.application.product_diff.compare import ProductDiffCompareError, compare_staging_to_item
from batch.application.product_diff.models import (
    ProductDiffPlan,
    ProductDiffSyncResult,
    StagingItemSeed,
)
from batch.application.product_diff.repositories import ProductDiffRepositories
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger

BATCH_ID = "BATCH-006"
PRODUCT_DIFF_PHASES: tuple[str, ...] = (
    "plan",
    "load_staging",
    "resolve_item",
    "compare",
    "persist",
    "status",
    "finalize",
)

DEFAULT_MAX_ITEMS = 1000
DEFAULT_SOURCE = "rakuten"
DEFAULT_SYNC_STAGING_DIFF_STATUS = True


def _is_batch_already_running(tracker: JobRunTracker) -> bool:
    """Scaffold tracker の unpaired running を検知（多重起動拒否用）。"""

    records = getattr(tracker, "records", None)
    if not isinstance(records, list):
        return False
    starts = 0
    completes = 0
    for record in records:
        if getattr(record, "batch_id", None) != BATCH_ID:
            continue
        status = getattr(record, "status", None)
        if status == "running":
            starts += 1
        elif status in {"succeeded", "partially_succeeded", "failed"}:
            completes += 1
    return starts > completes


class ProductDiffJob:
    """Orchestrates BATCH-006 Staging ↔ Item hash compare phases."""

    def __init__(
        self,
        *,
        repositories: ProductDiffRepositories,
        job_run_tracker: JobRunTracker | None = None,
        logger: BatchLogger | None = None,
    ) -> None:
        self._repos = repositories
        self._tracker = job_run_tracker or ScaffoldJobRunTracker()
        self._logger = logger or ScaffoldBatchLogger()


    @property
    def repositories(self):
        """Expose repositories for CLI bind_run / observability wiring."""

        return self._repos

    def run(
        self,
        *,
        job_run_id: str,
        batch_run_id: str | None = None,
        max_items: int | None = None,
        source: str | None = None,
        staging_item_ids: Sequence[str] | None = None,
        external_item_codes: Sequence[str] | None = None,
        force: bool = False,
        sync_staging_diff_status: bool | None = None,
        trace_id: str | None = None,
    ) -> ProductDiffSyncResult:
        # tracker は葉 job_run_id。product_diff_result 書込は共有 batch_run_id。
        business_run_id = (batch_run_id or "").strip() or job_run_id
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        result = ProductDiffSyncResult(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")

        if _is_batch_already_running(self._tracker):
            result.error_codes.append("GRS-BAT-003")
            self._repos.record_error(code="GRS-BAT-003", summary="batch already running")
            bound_logger.error("product_diff.already_running", batch_id=BATCH_ID)
            return result

        self._tracker.start(batch_id=BATCH_ID, job_run_id=job_run_id)

        try:
            plan = self._phase_plan(
                max_items=max_items,
                source=source,
                staging_item_ids=staging_item_ids,
                external_item_codes=external_item_codes,
                force=force,
                sync_staging_diff_status=sync_staging_diff_status,
            )
            result.planned_staging_count = len(plan.items)
            result.completed_phases.append("plan")
            self._repos.record_phase(phase="plan", status="succeeded")
            bound_logger.info("product_diff.plan", staging_count=len(plan.items))

            if not plan.items:
                # 未判定 Staging が無い → 冪等 noop 成功
                if self._repos.staging_items and not force:
                    result.status = "succeeded"
                    self._tracker.complete(
                        batch_id=BATCH_ID, job_run_id=job_run_id, status="succeeded"
                    )
                    self._repos.record_phase(phase="finalize", status="succeeded")
                    result.completed_phases.append("finalize")
                    bound_logger.info(
                        "product_diff.plan_empty_noop",
                        reason="already_judged_or_filtered",
                    )
                    return result
                result.status = "failed"
                result.error_codes.append("GRS-BAT-001")
                self._repos.record_error(code="GRS-BAT-001", summary="empty product_diff_plan")
                self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
                result.completed_phases.append("finalize")
                return result

            phases_seen: set[str] = {"plan"}
            for seed in plan.items:
                try:
                    self._process_one_staging(
                        seed=seed,
                        batch_run_id=business_run_id,
                        sync_staging=plan.sync_staging_diff_status,
                        result=result,
                        phases_seen=phases_seen,
                    )
                    result.succeeded_external_codes.append(seed.external_item_code)
                except ProductDiffCompareError as exc:
                    result.failed_external_codes.append(seed.external_item_code)
                    result.error_codes.append(exc.code)
                    self._repos.record_error(
                        code=exc.code,
                        summary=exc.message,
                        external_item_code=seed.external_item_code,
                        staging_item_id=seed.staging_item_id,
                    )
                    bound_logger.error(
                        "product_diff.compare_failed",
                        external_item_code=seed.external_item_code,
                        error_code=exc.code,
                    )
                except KeyError as exc:
                    result.failed_external_codes.append(seed.external_item_code)
                    result.error_codes.append("GRS-DB-001")
                    self._repos.record_error(
                        code="GRS-DB-001",
                        summary=str(exc),
                        external_item_code=seed.external_item_code,
                        staging_item_id=seed.staging_item_id,
                    )
                except Exception as exc:  # noqa: BLE001 — finalize partial failure
                    result.failed_external_codes.append(seed.external_item_code)
                    result.error_codes.append("GRS-BAT-007")
                    self._repos.record_error(
                        code="GRS-BAT-007",
                        summary=str(exc),
                        external_item_code=seed.external_item_code,
                        staging_item_id=seed.staging_item_id,
                    )
                    bound_logger.error(
                        "product_diff.unexpected_failure",
                        external_item_code=seed.external_item_code,
                    )

            for phase in (
                "load_staging",
                "resolve_item",
                "compare",
                "persist",
                "status",
            ):
                if phase not in result.completed_phases:
                    result.completed_phases.append(phase)

            result.written_item_rows = list(self._repos.written_item_rows)
            result.written_item_image_rows = list(self._repos.written_item_image_rows)
            result.written_active_status_rows = list(self._repos.written_active_status_rows)
            result.hash_recalculate_calls = list(self._repos.hash_recalculate_calls)

            result = self._phase_finalize(result)
            bound_logger.info(
                "product_diff.finalize",
                status=result.status,
                succeeded=len(result.succeeded_external_codes),
                failed=len(result.failed_external_codes),
                new=result.diff_new_count,
                updated=result.diff_updated_count,
                unchanged=result.diff_unchanged_count,
                unavailable=result.diff_unavailable_count,
            )
            return result
        except Exception:
            self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
            raise

    def _phase_plan(
        self,
        *,
        max_items: int | None,
        source: str | None,
        staging_item_ids: Sequence[str] | None,
        external_item_codes: Sequence[str] | None,
        force: bool,
        sync_staging_diff_status: bool | None,
    ) -> ProductDiffPlan:
        resolved_max = DEFAULT_MAX_ITEMS if max_items is None else max(0, int(max_items))
        resolved_source = (source or DEFAULT_SOURCE).strip() or DEFAULT_SOURCE
        sync = (
            DEFAULT_SYNC_STAGING_DIFF_STATUS
            if sync_staging_diff_status is None
            else bool(sync_staging_diff_status)
        )

        ids = (
            tuple(str(i).strip() for i in staging_item_ids if str(i).strip())
            if staging_item_ids
            else None
        )
        codes = (
            tuple(str(c).strip() for c in external_item_codes if str(c).strip())
            if external_item_codes
            else None
        )
        items = self._repos.list_eligible_staging(
            max_items=resolved_max,
            source=resolved_source,
            staging_item_ids=ids,
            external_item_codes=codes,
            force=force,
        )
        return ProductDiffPlan(
            items=tuple(items),
            source_filter=resolved_source,
            max_items=resolved_max,
            force=force,
            sync_staging_diff_status=sync,
        )

    def _process_one_staging(
        self,
        *,
        seed: StagingItemSeed,
        batch_run_id: str,
        sync_staging: bool,
        result: ProductDiffSyncResult,
        phases_seen: set[str],
    ) -> None:
        # load_staging
        staging = self._repos.load_staging(staging_item_id=seed.staging_item_id)
        phases_seen.add("load_staging")
        if "load_staging" not in result.completed_phases:
            result.completed_phases.append("load_staging")
            self._repos.record_phase(phase="load_staging", status="succeeded")

        # resolve_item（未存在はエラーではない）
        item = self._repos.resolve_item(
            source=staging.source,
            external_item_code=staging.external_item_code,
        )
        phases_seen.add("resolve_item")
        if "resolve_item" not in result.completed_phases:
            result.completed_phases.append("resolve_item")
            self._repos.record_phase(phase="resolve_item", status="succeeded")

        # compare（hash 再算出なし）
        judgment = compare_staging_to_item(
            staging=staging,
            item=item,
            judged_at=datetime.now(UTC),
        )
        phases_seen.add("compare")
        if "compare" not in result.completed_phases:
            result.completed_phases.append("compare")
            self._repos.record_phase(phase="compare", status="succeeded")

        # persist
        self._repos.upsert_product_diff(batch_run_id=batch_run_id, judgment=judgment)
        result.product_diff_upsert_count += 1
        if judgment.diff_status == "new":
            result.diff_new_count += 1
        elif judgment.diff_status == "updated":
            result.diff_updated_count += 1
        elif judgment.diff_status == "unchanged":
            result.diff_unchanged_count += 1
        elif judgment.diff_status == "unavailable":
            result.diff_unavailable_count += 1
        phases_seen.add("persist")
        if "persist" not in result.completed_phases:
            result.completed_phases.append("persist")
            self._repos.record_phase(phase="persist", status="succeeded")

        # status（Staging 同期。既定 ON）
        if sync_staging:
            self._repos.sync_staging_diff_status(
                staging_item_id=staging.staging_item_id,
                diff_status=judgment.diff_status,
            )
            result.staging_diff_status_sync_count += 1
        phases_seen.add("status")
        if "status" not in result.completed_phases:
            result.completed_phases.append("status")
            self._repos.record_phase(phase="status", status="succeeded")

    def _phase_finalize(self, result: ProductDiffSyncResult) -> ProductDiffSyncResult:
        if result.failed_external_codes and result.succeeded_external_codes:
            result.status = "partially_succeeded"
            if "GRS-BAT-002" not in result.error_codes:
                result.error_codes.append("GRS-BAT-002")
            tracker_status = "partially_succeeded"
        elif result.failed_external_codes and not result.succeeded_external_codes:
            result.status = "failed"
            if "GRS-BAT-001" not in result.error_codes:
                result.error_codes.append("GRS-BAT-001")
            tracker_status = "failed"
        elif result.succeeded_external_codes:
            result.status = "succeeded"
            tracker_status = "succeeded"
        else:
            result.status = "failed"
            tracker_status = "failed"

        self._tracker.complete(
            batch_id=BATCH_ID,
            job_run_id=result.job_run_id,
            status=tracker_status,
        )
        self._repos.record_phase(phase="finalize", status=result.status)
        result.completed_phases.append("finalize")
        return result
