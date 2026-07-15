"""BATCH-005 Raw取込・Staging変換ジョブ実装.

処理 Phase（仕様書 §8.2）:
plan → read → transform → validate → persist → status → finalize
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from batch.application.job_run import JobRunTracker, ScaffoldJobRunTracker
from batch.application.raw_staging.models import (
    RawMetadataSeed,
    RawStagingSyncResult,
    StagingPlan,
)
from batch.application.raw_staging.repositories import RawStagingRepositories
from batch.application.raw_staging.transform import StagingTransformError, transform_raw
from batch.application.raw_staging.validate import StagingValidationError, validate_transform_result
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger
from batch.infrastructure.object_storage import ObjectStorageError

BATCH_ID = "BATCH-005"
RAW_STAGING_PHASES: tuple[str, ...] = (
    "plan",
    "read",
    "transform",
    "validate",
    "persist",
    "status",
    "finalize",
)

DEFAULT_MAX_RAW = 1000
DEFAULT_SOURCE_API = "item_search"


class RawStagingJob:
    """Orchestrates BATCH-005 Raw → Staging phases."""

    def __init__(
        self,
        *,
        repositories: RawStagingRepositories,
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
        max_raw: int | None = None,
        source_api: str | Sequence[str] | None = None,
        raw_metadata_ids: Sequence[str] | None = None,
        force: bool = False,
        trace_id: str | None = None,
    ) -> RawStagingSyncResult:
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        self._tracker.start(batch_id=BATCH_ID, job_run_id=job_run_id)

        result = RawStagingSyncResult(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")

        try:
            plan = self._phase_plan(
                max_raw=max_raw,
                source_api=source_api,
                raw_metadata_ids=raw_metadata_ids,
                force=force,
            )
            result.planned_raw_count = len(plan.items)
            result.completed_phases.append("plan")
            self._repos.record_phase(phase="plan", status="succeeded")
            bound_logger.info("raw_staging.plan", raw_count=len(plan.items))

            if not plan.items:
                # 既に staged/imported のみで選定 0 件 → 冪等再実行として成功扱い
                if self._repos.raw_metadata and not force:
                    result.status = "succeeded"
                    self._tracker.complete(
                        batch_id=BATCH_ID, job_run_id=job_run_id, status="succeeded"
                    )
                    self._repos.record_phase(phase="finalize", status="succeeded")
                    result.completed_phases.append("finalize")
                    bound_logger.info("raw_staging.plan_empty_noop", reason="already_staged_or_filtered")
                    return result
                result.status = "failed"
                result.error_codes.append("GRS-BAT-001")
                self._repos.record_error(code="GRS-BAT-001", summary="empty staging_plan")
                self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
                result.completed_phases.append("finalize")
                return result

            phases_seen: set[str] = {"plan"}
            for meta in plan.items:
                try:
                    outcome = self._process_one_raw(
                        meta=meta, result=result, phases_seen=phases_seen
                    )
                    if outcome == "skipped":
                        # already recorded on result.skipped_raw_ids
                        pass
                    else:
                        result.succeeded_raw_ids.append(meta.raw_metadata_id)
                except ObjectStorageError as exc:
                    result.failed_raw_ids.append(meta.raw_metadata_id)
                    result.error_codes.append(exc.code)
                    self._repos.mark_failed(raw_metadata_id=meta.raw_metadata_id, error_code=exc.code)
                    self._repos.record_error(
                        code=exc.code,
                        summary=exc.message,
                        raw_metadata_id=meta.raw_metadata_id,
                    )
                    bound_logger.error(
                        "raw_staging.raw_failed",
                        raw_metadata_id=meta.raw_metadata_id,
                        error_code=exc.code,
                    )
                except StagingTransformError as exc:
                    result.failed_raw_ids.append(meta.raw_metadata_id)
                    result.error_codes.append(exc.code)
                    self._repos.mark_failed(raw_metadata_id=meta.raw_metadata_id, error_code=exc.code)
                    self._repos.record_error(
                        code=exc.code,
                        summary=exc.message,
                        raw_metadata_id=meta.raw_metadata_id,
                    )
                except StagingValidationError as exc:
                    result.failed_raw_ids.append(meta.raw_metadata_id)
                    result.error_codes.append(exc.code)
                    result.validation_reject_count += 1
                    self._repos.mark_failed(raw_metadata_id=meta.raw_metadata_id, error_code=exc.code)
                    self._repos.record_error(
                        code=exc.code,
                        summary=exc.message,
                        raw_metadata_id=meta.raw_metadata_id,
                    )
                except Exception as exc:  # noqa: BLE001 — finalize partial failure
                    result.failed_raw_ids.append(meta.raw_metadata_id)
                    result.error_codes.append("GRS-BAT-001")
                    self._repos.mark_failed(
                        raw_metadata_id=meta.raw_metadata_id,
                        error_code="GRS-BAT-001",
                    )
                    self._repos.record_error(
                        code="GRS-BAT-001",
                        summary=str(exc),
                        raw_metadata_id=meta.raw_metadata_id,
                    )
                    bound_logger.error(
                        "raw_staging.unexpected_failure",
                        raw_metadata_id=meta.raw_metadata_id,
                    )

            for phase in ("read", "transform", "validate", "persist", "status"):
                if phase not in result.completed_phases:
                    result.completed_phases.append(phase)

            result.written_item_rows = list(self._repos.written_item_rows)
            result.written_product_diff_rows = list(self._repos.written_product_diff_rows)
            result.written_active_status_rows = list(self._repos.written_active_status_rows)
            result.written_external_genre_rows = list(self._repos.written_external_genre_rows)
            result.object_storage_put_count = self._repos.object_storage_put_count
            result.object_storage_delete_count = self._repos.object_storage_delete_count

            # Detect accidental puts on ScaffoldObjectStorageClient if present
            put_calls = getattr(self._repos.object_storage, "put_calls", None)
            if isinstance(put_calls, list):
                result.object_storage_put_count = len(put_calls)

            result = self._phase_finalize(result)
            bound_logger.info(
                "raw_staging.finalize",
                status=result.status,
                succeeded=len(result.succeeded_raw_ids),
                failed=len(result.failed_raw_ids),
                skipped=len(result.skipped_raw_ids),
            )
            return result
        except Exception:
            self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
            raise

    def _phase_plan(
        self,
        *,
        max_raw: int | None,
        source_api: str | Sequence[str] | None,
        raw_metadata_ids: Sequence[str] | None,
        force: bool,
    ) -> StagingPlan:
        resolved_max = DEFAULT_MAX_RAW if max_raw is None else max(0, int(max_raw))
        if source_api is None:
            apis: tuple[str, ...] = (DEFAULT_SOURCE_API,)
        elif isinstance(source_api, str):
            apis = tuple(part.strip() for part in source_api.split(",") if part.strip()) or (
                DEFAULT_SOURCE_API,
            )
        else:
            apis = tuple(str(a).strip() for a in source_api if str(a).strip()) or (
                DEFAULT_SOURCE_API,
            )

        ids = (
            tuple(str(i).strip() for i in raw_metadata_ids if str(i).strip())
            if raw_metadata_ids
            else None
        )
        items = self._repos.list_eligible_raws(
            max_raw=resolved_max,
            source_apis=apis,
            raw_metadata_ids=ids,
            force=force,
        )
        return StagingPlan(
            items=tuple(items),
            source_api_filter=apis,
            max_raw=resolved_max,
            force=force,
        )

    def _process_one_raw(
        self,
        *,
        meta: RawMetadataSeed,
        result: RawStagingSyncResult,
        phases_seen: set[str],
    ) -> str:
        """Process one Raw. Returns ``succeeded`` or ``skipped``."""

        # read
        body = self._repos.read_raw_body(meta=meta)
        phases_seen.add("read")
        if "read" not in result.completed_phases:
            result.completed_phases.append("read")
            self._repos.record_phase(phase="read", status="succeeded")

        # transform
        staged_at = datetime.now(UTC)
        transformed = transform_raw(meta=meta, body=body, staged_at=staged_at)
        phases_seen.add("transform")
        if "transform" not in result.completed_phases:
            result.completed_phases.append("transform")
            self._repos.record_phase(phase="transform", status="succeeded")

        if transformed.skipped:
            # stub path: count as skip (not failure); do not mark staged
            result.skipped_raw_ids.append(meta.raw_metadata_id)
            return "skipped"

        # validate
        accepted = validate_transform_result(transformed)
        phases_seen.add("validate")
        if "validate" not in result.completed_phases:
            result.completed_phases.append("validate")
            self._repos.record_phase(phase="validate", status="succeeded")

        if not accepted:
            raise StagingValidationError(
                code="GRS-VAL-001",
                message="no valid staging items in raw",
            )

        # persist
        item_count, image_count = self._repos.persist_item_bundles(accepted)
        result.staging_item_upsert_count += item_count
        result.staging_item_image_upsert_count += image_count
        phases_seen.add("persist")
        if "persist" not in result.completed_phases:
            result.completed_phases.append("persist")
            self._repos.record_phase(phase="persist", status="succeeded")

        # status
        self._repos.mark_staged(raw_metadata_id=meta.raw_metadata_id, staged_at=staged_at)
        phases_seen.add("status")
        if "status" not in result.completed_phases:
            result.completed_phases.append("status")
            self._repos.record_phase(phase="status", status="succeeded")
        return "succeeded"

    def _phase_finalize(self, result: RawStagingSyncResult) -> RawStagingSyncResult:
        # Skips that never raised are removed from succeeded if we added them incorrectly.
        # Current flow: skipped returns early without appending to succeeded — OK.
        if result.failed_raw_ids and result.succeeded_raw_ids:
            result.status = "partially_succeeded"
            if "GRS-BAT-002" not in result.error_codes:
                result.error_codes.append("GRS-BAT-002")
            tracker_status = "partially_succeeded"
        elif result.failed_raw_ids and not result.succeeded_raw_ids:
            result.status = "failed"
            if "GRS-BAT-001" not in result.error_codes:
                result.error_codes.append("GRS-BAT-001")
            tracker_status = "failed"
        elif result.succeeded_raw_ids:
            result.status = "succeeded"
            tracker_status = "succeeded"
        elif result.skipped_raw_ids and not result.failed_raw_ids:
            # All stubs skipped — treat as succeeded with no staging writes
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
