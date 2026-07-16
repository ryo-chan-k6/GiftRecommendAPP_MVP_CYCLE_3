"""BATCH-007 Item反映ジョブ実装.

処理 Phase（仕様書 §8.2）:
plan → load_diff → load_staging → apply_item → apply_images → apply_review → finalize
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from batch.application.item_apply.models import (
    ItemApplyPlan,
    ItemApplySyncResult,
    ProductDiffResultSeed,
)
from batch.application.item_apply.repositories import ItemApplyRepositories
from batch.application.job_run import JobRunTracker, ScaffoldJobRunTracker
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger

BATCH_ID = "BATCH-007"
ITEM_APPLY_PHASES: tuple[str, ...] = (
    "plan",
    "load_diff",
    "load_staging",
    "apply_item",
    "apply_images",
    "apply_review",
    "finalize",
)

DEFAULT_MAX_ITEMS = 1000
DEFAULT_SOURCE = "rakuten"


class ItemApplyError(Exception):
    """Per-item apply failure with batch error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


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


class ItemApplyJob:
    """Orchestrates BATCH-007 Diff → Item / Image / Review apply phases."""

    def __init__(
        self,
        *,
        repositories: ItemApplyRepositories,
        job_run_tracker: JobRunTracker | None = None,
        logger: BatchLogger | None = None,
    ) -> None:
        self._repos = repositories
        self._tracker = job_run_tracker or ScaffoldJobRunTracker()
        self._logger = logger or ScaffoldBatchLogger()

    def run(
        self,
        *,
        job_run_id: str,
        max_items: int | None = None,
        source: str | None = None,
        diff_batch_run_id: str | None = None,
        external_item_codes: Sequence[str] | None = None,
        staging_item_ids: Sequence[str] | None = None,
        trace_id: str | None = None,
    ) -> ItemApplySyncResult:
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        result = ItemApplySyncResult(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")

        if _is_batch_already_running(self._tracker):
            result.error_codes.append("GRS-BAT-003")
            self._repos.record_error(code="GRS-BAT-003", summary="batch already running")
            bound_logger.error("item_apply.already_running", batch_id=BATCH_ID)
            return result

        self._tracker.start(batch_id=BATCH_ID, job_run_id=job_run_id)

        try:
            plan = self._phase_plan(
                max_items=max_items,
                source=source,
                diff_batch_run_id=diff_batch_run_id,
                external_item_codes=external_item_codes,
                staging_item_ids=staging_item_ids,
            )
            result.planned_diff_count = len(plan.items)
            result.item_unavailable_skip_count = plan.unavailable_skip_count
            result.completed_phases.append("plan")
            self._repos.record_phase(phase="plan", status="succeeded")
            bound_logger.info(
                "item_apply.plan",
                processable=len(plan.items),
                unavailable_skip=plan.unavailable_skip_count,
            )

            if not plan.items and plan.unavailable_skip_count == 0:
                if self._repos.product_diff_results:
                    # filtered empty → idempotent noop success
                    result.status = "succeeded"
                    self._tracker.complete(
                        batch_id=BATCH_ID, job_run_id=job_run_id, status="succeeded"
                    )
                    self._repos.record_phase(phase="finalize", status="succeeded")
                    result.completed_phases.append("finalize")
                    bound_logger.info("item_apply.plan_empty_noop", reason="filtered_empty")
                    return result
                result.status = "failed"
                result.error_codes.append("GRS-BAT-001")
                self._repos.record_error(code="GRS-BAT-001", summary="empty item_apply_plan")
                self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
                result.completed_phases.append("finalize")
                return result

            if not plan.items and plan.unavailable_skip_count > 0:
                # only unavailable → succeeded with skip aggregation
                result = self._phase_finalize(result)
                bound_logger.info(
                    "item_apply.finalize_unavailable_only",
                    unavailable_skip=result.item_unavailable_skip_count,
                )
                return result

            run_at = datetime.now(UTC)
            for seed in plan.items:
                try:
                    self._process_one_diff(
                        seed=seed,
                        run_at=run_at,
                        result=result,
                    )
                    result.succeeded_external_codes.append(seed.external_item_code)
                except ItemApplyError as exc:
                    result.failed_external_codes.append(seed.external_item_code)
                    result.error_codes.append(exc.code)
                    self._repos.record_error(
                        code=exc.code,
                        summary=exc.message,
                        external_item_code=seed.external_item_code,
                        staging_item_id=seed.staging_item_id,
                    )
                    bound_logger.error(
                        "item_apply.apply_failed",
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
                        "item_apply.unexpected_failure",
                        external_item_code=seed.external_item_code,
                    )

            for phase in (
                "load_diff",
                "load_staging",
                "apply_item",
                "apply_images",
                "apply_review",
            ):
                if phase not in result.completed_phases:
                    result.completed_phases.append(phase)

            result.written_item_rows = list(self._repos.written_item_rows)
            result.written_item_image_rows = list(self._repos.written_item_image_rows)
            result.written_item_review_rows = list(self._repos.written_item_review_rows)
            result.written_active_status_rows = list(self._repos.written_active_status_rows)
            result.product_diff_write_count = self._repos.product_diff_write_count
            result.hash_recalculate_calls = list(self._repos.hash_recalculate_calls)

            result = self._phase_finalize(result)
            bound_logger.info(
                "item_apply.finalize",
                status=result.status,
                succeeded=len(result.succeeded_external_codes),
                failed=len(result.failed_external_codes),
                upserts=result.item_upsert_count,
                unchanged_touch=result.item_unchanged_touch_count,
                unavailable_skip=result.item_unavailable_skip_count,
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
        diff_batch_run_id: str | None,
        external_item_codes: Sequence[str] | None,
        staging_item_ids: Sequence[str] | None,
    ) -> ItemApplyPlan:
        resolved_max = DEFAULT_MAX_ITEMS if max_items is None else max(0, int(max_items))
        resolved_source = (source or DEFAULT_SOURCE).strip() or DEFAULT_SOURCE
        resolved_diff_run = (
            diff_batch_run_id.strip() if diff_batch_run_id and diff_batch_run_id.strip() else None
        )
        codes = (
            tuple(str(c).strip() for c in external_item_codes if str(c).strip())
            if external_item_codes
            else None
        )
        staging_ids = (
            tuple(str(i).strip() for i in staging_item_ids if str(i).strip())
            if staging_item_ids
            else None
        )
        items, unavailable_count = self._repos.list_eligible_diffs(
            max_items=resolved_max,
            source=resolved_source,
            diff_batch_run_id=resolved_diff_run,
            external_item_codes=codes,
            staging_item_ids=staging_ids,
        )
        return ItemApplyPlan(
            items=tuple(items),
            unavailable_skip_count=unavailable_count,
            source_filter=resolved_source,
            max_items=resolved_max,
            diff_batch_run_id=resolved_diff_run,
        )

    def _process_one_diff(
        self,
        *,
        seed: ProductDiffResultSeed,
        run_at: datetime,
        result: ItemApplySyncResult,
    ) -> None:
        # load_diff
        diff = self._repos.load_diff(product_diff_result_id=seed.product_diff_result_id)
        if "load_diff" not in result.completed_phases:
            result.completed_phases.append("load_diff")
            self._repos.record_phase(phase="load_diff", status="succeeded")

        if diff.diff_status == "unavailable":
            # defensive: plan should exclude; count as skip and return
            result.item_unavailable_skip_count += 1
            result.skipped_external_codes.append(diff.external_item_code)
            return

        # load_staging
        staging = self._repos.load_staging(staging_item_id=diff.staging_item_id)
        if "load_staging" not in result.completed_phases:
            result.completed_phases.append("load_staging")
            self._repos.record_phase(phase="load_staging", status="succeeded")

        images = self._repos.load_staging_images(staging_item_id=staging.staging_item_id)

        # apply_item
        if diff.diff_status in {"new", "updated"}:
            if staging.normalized_hash is None:
                raise ItemApplyError(
                    "GRS-BAT-005",
                    "normalized_hash is NULL; re-staging required before apply",
                )
            item_row = self._repos.upsert_item_from_staging(
                staging=staging,
                checked_at=run_at,
                is_new=diff.diff_status == "new",
            )
            result.item_upsert_count += 1
            item_id = str(item_row["item_id"])
        elif diff.diff_status == "unchanged":
            item_row = self._repos.touch_item_last_checked(
                source=staging.source,
                external_item_code=staging.external_item_code,
                checked_at=run_at,
            )
            result.item_unchanged_touch_count += 1
            item_id = str(item_row["item_id"])
        else:
            raise ItemApplyError("GRS-BAT-005", f"unsupported diff_status: {diff.diff_status}")

        if "apply_item" not in result.completed_phases:
            result.completed_phases.append("apply_item")
            self._repos.record_phase(phase="apply_item", status="succeeded")

        # apply_images — new/updated only; unchanged no-op
        if diff.diff_status in {"new", "updated"}:
            self._repos.sync_item_images(item_id=item_id, images=images, fetched_at=run_at)
            result.item_image_sync_count += 1
        if "apply_images" not in result.completed_phases:
            result.completed_phases.append("apply_images")
            self._repos.record_phase(phase="apply_images", status="succeeded")

        # apply_review — new/updated only; missing columns → skip (no DELETE)
        if diff.diff_status in {"new", "updated"}:
            review = self._repos.upsert_item_review(
                item_id=item_id,
                review_average=staging.review_average,
                review_count=staging.review_count,
                fetched_at=run_at,
            )
            if review is None:
                result.item_review_skip_count += 1
            else:
                result.item_review_upsert_count += 1
        if "apply_review" not in result.completed_phases:
            result.completed_phases.append("apply_review")
            self._repos.record_phase(phase="apply_review", status="succeeded")

    def _phase_finalize(self, result: ItemApplySyncResult) -> ItemApplySyncResult:
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
        elif result.succeeded_external_codes or result.item_unavailable_skip_count > 0:
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
