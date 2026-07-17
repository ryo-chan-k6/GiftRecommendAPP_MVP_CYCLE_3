"""BATCH-009 商品意味生成キュー登録ジョブ実装.

処理 Phase（仕様書 §8.2）:
plan → load_item → filter_active → load_diff → evaluate → resolve_config →
resolve_feature → register → finalize
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from batch.application.item_generation_queue.evaluate import evaluate_registration
from batch.application.item_generation_queue.models import (
    ConfigResolveHint,
    FeatureResolveHint,
    ItemGenerationQueueResult,
    ProductDiffRow,
    RegistrationPlan,
)
from batch.application.item_generation_queue.repositories import ItemGenerationQueueRepositories
from batch.application.job_run import JobRunTracker, ScaffoldJobRunTracker
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger

BATCH_ID = "BATCH-009"
ITEM_GENERATION_QUEUE_PHASES: tuple[str, ...] = (
    "plan",
    "load_item",
    "filter_active",
    "load_diff",
    "evaluate",
    "resolve_config",
    "resolve_feature",
    "register",
    "finalize",
)

DEFAULT_MAX_ITEMS = 1000
DEFAULT_SOURCE = "rakuten"


class ItemGenerationQueueError(Exception):
    """Per-item registration failure with batch error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _is_batch_already_running(tracker: JobRunTracker) -> bool:
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


def resolve_config_version(*, item_id: str) -> ConfigResolveHint:
    """MVP scaffold stub — no real Reco module call (§8.2 resolve_config)."""

    _ = item_id
    return ConfigResolveHint(semantic_config_version_id="scaffold-semantic-config-v1")


def resolve_feature_input(*, item_id: str) -> FeatureResolveHint:
    """MVP scaffold stub — no real Reco module call (§8.2 resolve_feature)."""

    _ = item_id
    return FeatureResolveHint(feature_input_hash="scaffold-feature-hash")


class ItemGenerationQueueJob:
    """Orchestrates BATCH-009 queue registration phases."""

    def __init__(
        self,
        *,
        repositories: ItemGenerationQueueRepositories,
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
        trace_id: str | None = None,
    ) -> ItemGenerationQueueResult:
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        result = ItemGenerationQueueResult(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")

        if _is_batch_already_running(self._tracker):
            result.error_codes.append("GRS-BAT-003")
            self._repos.record_error(code="GRS-BAT-003", summary="batch already running")
            bound_logger.error("item_generation_queue.already_running", batch_id=BATCH_ID)
            return result

        self._tracker.start(batch_id=BATCH_ID, job_run_id=job_run_id)

        try:
            plan = self._phase_plan(
                max_items=max_items,
                source=source,
                diff_batch_run_id=diff_batch_run_id,
                external_item_codes=external_item_codes,
            )
            result.planned_diff_count = len(plan.items)
            result.queue_unavailable_skip_count = plan.unavailable_skip_count
            result.queue_unchanged_skip_count = plan.unchanged_skip_count
            result.completed_phases.append("plan")
            self._repos.record_phase(phase="plan", status="succeeded")
            bound_logger.info(
                "item_generation_queue.plan",
                processable=len(plan.items),
                unavailable_skip=plan.unavailable_skip_count,
                unchanged_skip=plan.unchanged_skip_count,
            )

            if not plan.items and plan.unavailable_skip_count == 0 and plan.unchanged_skip_count == 0:
                if self._repos.product_diff_results:
                    result.status = "succeeded"
                    self._tracker.complete(
                        batch_id=BATCH_ID, job_run_id=job_run_id, status="succeeded"
                    )
                    self._repos.record_phase(phase="finalize", status="succeeded")
                    result.completed_phases.append("finalize")
                    bound_logger.info("item_generation_queue.plan_empty_noop", reason="filtered_empty")
                    return result
                result.status = "failed"
                result.error_codes.append("GRS-BAT-001")
                self._repos.record_error(code="GRS-BAT-001", summary="empty registration plan")
                self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
                result.completed_phases.append("finalize")
                return result

            run_at = datetime.now(UTC)
            for seed in plan.items:
                try:
                    self._process_one(
                        seed=seed,
                        source=plan.source_filter,
                        run_at=run_at,
                        result=result,
                    )
                    if seed.external_item_code not in result.failed_external_codes:
                        if seed.external_item_code not in result.skipped_external_codes:
                            result.succeeded_external_codes.append(seed.external_item_code)
                except ItemGenerationQueueError as exc:
                    result.failed_external_codes.append(seed.external_item_code)
                    result.error_codes.append(exc.code)
                    result.queue_register_failed_count += 1
                    self._repos.record_error(
                        code=exc.code,
                        summary=exc.message,
                        external_item_code=seed.external_item_code,
                    )
                    bound_logger.error(
                        "item_generation_queue.register_failed",
                        external_item_code=seed.external_item_code,
                        error_code=exc.code,
                    )
                except KeyError as exc:
                    result.failed_external_codes.append(seed.external_item_code)
                    result.error_codes.append("GRS-DB-001")
                    result.queue_register_failed_count += 1
                    self._repos.record_error(
                        code="GRS-DB-001",
                        summary=str(exc),
                        external_item_code=seed.external_item_code,
                    )
                except Exception as exc:  # noqa: BLE001 — per-item failure continues
                    result.failed_external_codes.append(seed.external_item_code)
                    result.error_codes.append("GRS-BAT-005")
                    result.queue_register_failed_count += 1
                    self._repos.record_error(
                        code="GRS-BAT-005",
                        summary=str(exc),
                        external_item_code=seed.external_item_code,
                    )
                    bound_logger.error(
                        "item_generation_queue.unexpected_failure",
                        external_item_code=seed.external_item_code,
                    )

            for phase in (
                "load_item",
                "filter_active",
                "load_diff",
                "evaluate",
                "resolve_config",
                "resolve_feature",
                "register",
            ):
                if phase not in result.completed_phases:
                    result.completed_phases.append(phase)

            result.written_queue_rows = list(self._repos.written_queue_rows)
            result.item_write_count = self._repos.item_write_count
            result.product_diff_write_count = self._repos.product_diff_write_count

            result = self._phase_finalize(result)
            bound_logger.info(
                "item_generation_queue.finalize",
                status=result.status,
                inserted=result.queue_inserted_count,
                queued_at_touch=result.queue_queued_at_updated_count,
                skipped=len(result.skipped_external_codes),
                failed=len(result.failed_external_codes),
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
    ) -> RegistrationPlan:
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
        items, unavailable_count, unchanged_count = self._repos.list_eligible_diffs(
            max_items=resolved_max,
            source=resolved_source,
            diff_batch_run_id=resolved_diff_run,
            external_item_codes=codes,
        )
        return RegistrationPlan(
            items=tuple(items),
            unavailable_skip_count=unavailable_count,
            unchanged_skip_count=unchanged_count,
            source_filter=resolved_source,
            max_items=resolved_max,
            diff_batch_run_id=resolved_diff_run,
        )

    def _process_one(
        self,
        *,
        seed: ProductDiffRow,
        source: str,
        run_at: datetime,
        result: ItemGenerationQueueResult,
    ) -> None:
        code = seed.external_item_code

        # load_item
        item = self._repos.load_item(source=source, external_item_code=code)
        if "load_item" not in result.completed_phases:
            result.completed_phases.append("load_item")
            self._repos.record_phase(phase="load_item", status="succeeded")

        # filter_active
        if item.active_status != "active" or not item.is_active:
            result.queue_inactive_skip_count += 1
            result.skipped_external_codes.append(code)
            if "filter_active" not in result.completed_phases:
                result.completed_phases.append("filter_active")
                self._repos.record_phase(phase="filter_active", status="succeeded")
            return

        if "filter_active" not in result.completed_phases:
            result.completed_phases.append("filter_active")
            self._repos.record_phase(phase="filter_active", status="succeeded")

        # load_diff
        diff = self._repos.load_diff(product_diff_result_id=seed.product_diff_result_id)
        if "load_diff" not in result.completed_phases:
            result.completed_phases.append("load_diff")
            self._repos.record_phase(phase="load_diff", status="succeeded")

        # evaluate
        decision = evaluate_registration(item=item, diff=diff)
        if "evaluate" not in result.completed_phases:
            result.completed_phases.append("evaluate")
            self._repos.record_phase(phase="evaluate", status="succeeded")

        if not decision.should_register:
            if decision.skip_reason == "non_meaning_only":
                result.queue_non_meaning_skip_count += 1
            result.skipped_external_codes.append(code)
            return

        assert decision.generation_type is not None

        # resolve_config / resolve_feature (stubs)
        _ = resolve_config_version(item_id=item.item_id)
        _ = resolve_feature_input(item_id=item.item_id)
        if "resolve_config" not in result.completed_phases:
            result.completed_phases.append("resolve_config")
            self._repos.record_phase(phase="resolve_config", status="succeeded")
        if "resolve_feature" not in result.completed_phases:
            result.completed_phases.append("resolve_feature")
            self._repos.record_phase(phase="resolve_feature", status="succeeded")

        # register
        active = self._repos.find_active_queue(
            item_id=item.item_id,
            generation_type=decision.generation_type,
        )
        if active is not None and active["queue_status"] == "processing":
            result.queue_processing_skip_count += 1
            result.skipped_external_codes.append(code)
            if "register" not in result.completed_phases:
                result.completed_phases.append("register")
                self._repos.record_phase(phase="register", status="succeeded")
            return

        if active is not None and active["queue_status"] == "queued":
            self._repos.touch_queue_queued_at(
                item_generation_queue_id=str(active["item_generation_queue_id"]),
                queued_at=run_at,
            )
            result.queue_queued_at_updated_count += 1
        else:
            self._repos.insert_queue(
                item_id=item.item_id,
                generation_type=decision.generation_type,
                queued_at=run_at,
            )
            result.queue_inserted_count += 1
            if decision.generation_type == "semantic":
                result.queue_semantic_count += 1
            elif decision.generation_type == "feature":
                result.queue_feature_count += 1
            elif decision.generation_type == "embedding":
                result.queue_embedding_count += 1

        if "register" not in result.completed_phases:
            result.completed_phases.append("register")
            self._repos.record_phase(phase="register", status="succeeded")

    def _phase_finalize(self, result: ItemGenerationQueueResult) -> ItemGenerationQueueResult:
        if result.failed_external_codes and result.succeeded_external_codes:
            result.status = "partially_succeeded"
            if "GRS-BAT-002" not in result.error_codes:
                result.error_codes.append("GRS-BAT-002")
            tracker_status = "partially_succeeded"
        elif result.failed_external_codes and not result.succeeded_external_codes:
            if result.skipped_external_codes or result.queue_unavailable_skip_count:
                result.status = "partially_succeeded" if result.skipped_external_codes else "failed"
                tracker_status = result.status
            else:
                result.status = "failed"
                if "GRS-BAT-001" not in result.error_codes:
                    result.error_codes.append("GRS-BAT-001")
                tracker_status = "failed"
        elif (
            result.succeeded_external_codes
            or result.skipped_external_codes
            or result.queue_unavailable_skip_count
            or result.queue_unchanged_skip_count
        ):
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
