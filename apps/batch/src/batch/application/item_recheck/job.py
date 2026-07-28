"""BATCH-004 楽天既存商品再確認ジョブ実装.

処理 Phase（仕様書 §8.2）:
plan → cursor → fetch → adapt → raw_save → resolve → cursor_update → finalize
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence

from batch.application.item_recheck.idempotency import (
    SOURCE_RAKUTEN,
    build_item_search_raw_object_key,
    content_hash_for_payload,
)
from batch.application.item_recheck.models import (
    ItemRecheckSyncResult,
    ItemSeed,
    RawItemSearchArtifact,
    RecheckPlan,
)
from batch.application.item_recheck.repositories import ItemRecheckRepositories
from batch.application.item_recheck.resolve_candidate import resolve_active_status_candidate
from batch.application.job_run import JobRunTracker, ScaffoldJobRunTracker
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger
from batch.infrastructure.object_storage import ObjectStorageError
from batch.infrastructure.rakuten import (
    RakutenApiClient,
    RakutenItemSearchApiError,
    ScaffoldRakutenApiClient,
    adapt_item_search_raw_payload,
)

BATCH_ID = "BATCH-004"
ITEM_RECHECK_PHASES: tuple[str, ...] = (
    "plan",
    "cursor",
    "fetch",
    "adapt",
    "raw_save",
    "resolve",
    "cursor_update",
    "finalize",
)

DEFAULT_MAX_ITEMS = 1000
DEFAULT_HITS = 1


class ItemRecheckJob:
    """Orchestrates BATCH-004 existing-item recheck phases."""

    def __init__(
        self,
        *,
        rakuten_client: RakutenApiClient | None = None,
        repositories: ItemRecheckRepositories,
        job_run_tracker: JobRunTracker | None = None,
        logger: BatchLogger | None = None,
    ) -> None:
        self._rakuten = rakuten_client or ScaffoldRakutenApiClient()
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
        max_items: int | None = None,
        external_item_codes: Sequence[str] | None = None,
        hits: int | None = None,
        trace_id: str | None = None,
    ) -> ItemRecheckSyncResult:
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        self._tracker.start(batch_id=BATCH_ID, job_run_id=job_run_id)

        result = ItemRecheckSyncResult(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")

        try:
            plan = self._phase_plan(
                max_items=max_items,
                external_item_codes=external_item_codes,
                hits=hits,
            )
            result.planned_item_count = len(plan.items)
            result.completed_phases.append("plan")
            self._repos.record_phase(phase="plan", status="succeeded")
            bound_logger.info("item_recheck.plan", item_count=len(plan.items))

            if not plan.items:
                result.status = "failed"
                result.error_codes.append("GRS-BAT-001")
                self._repos.record_error(code="GRS-BAT-001", summary="empty recheck_plan")
                self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
                result.completed_phases.append("finalize")
                return result

            for item in plan.items:
                try:
                    self._recheck_one_item(
                        item=item,
                        hits=plan.hits,
                        job_run_id=job_run_id,
                        result=result,
                    )
                    result.succeeded_item_codes.append(item.external_item_code)
                except RakutenItemSearchApiError as exc:
                    result.failed_item_codes.append(item.external_item_code)
                    result.error_codes.append(exc.code)
                    self._repos.record_error(
                        code=exc.code,
                        summary=exc.message,
                        item_code=item.external_item_code,
                    )
                    bound_logger.error(
                        "item_recheck.item_failed",
                        external_item_code=item.external_item_code,
                        error_code=exc.code,
                    )
                except ObjectStorageError as exc:
                    result.failed_item_codes.append(item.external_item_code)
                    result.error_codes.append(exc.code)
                    self._repos.record_error(
                        code=exc.code,
                        summary=exc.message,
                        item_code=item.external_item_code,
                    )
                except Exception as exc:  # noqa: BLE001 — finalize partial failure
                    result.failed_item_codes.append(item.external_item_code)
                    result.error_codes.append("GRS-BAT-001")
                    self._repos.record_error(
                        code="GRS-BAT-001",
                        summary=str(exc),
                        item_code=item.external_item_code,
                    )
                    bound_logger.error(
                        "item_recheck.unexpected_failure",
                        external_item_code=item.external_item_code,
                    )

            for phase in ("cursor", "fetch", "adapt", "raw_save", "resolve", "cursor_update"):
                if phase not in result.completed_phases:
                    result.completed_phases.append(phase)

            result.created_items = list(self._repos.created_items)
            result.created_staging = list(self._repos.created_staging)
            result.updated_item_rows = list(self._repos.updated_item_rows)
            result = self._phase_finalize(result)
            bound_logger.info(
                "item_recheck.finalize",
                status=result.status,
                succeeded=len(result.succeeded_item_codes),
                failed=len(result.failed_item_codes),
            )
            return result
        except Exception:
            self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
            raise

    def _phase_plan(
        self,
        *,
        max_items: int | None,
        external_item_codes: Sequence[str] | None,
        hits: int | None,
    ) -> RecheckPlan:
        resolved_max = DEFAULT_MAX_ITEMS if max_items is None else max(0, int(max_items))
        resolved_hits = DEFAULT_HITS if hits is None else max(1, min(30, int(hits)))
        codes = (
            tuple(str(c).strip() for c in external_item_codes if str(c).strip())
            if external_item_codes
            else None
        )
        items = self._repos.list_seedable_items(
            max_items=resolved_max,
            external_item_codes=codes,
        )
        return RecheckPlan(source=SOURCE_RAKUTEN, items=tuple(items), hits=resolved_hits)

    def _recheck_one_item(
        self,
        *,
        item: ItemSeed,
        hits: int,
        job_run_id: str,
        result: ItemRecheckSyncResult,
    ) -> None:
        api_call_log_id = str(uuid.uuid4())
        page = 1

        # cursor
        cursor = self._repos.get_or_create_recheck_cursor(
            external_item_code=item.external_item_code
        )
        cursor_id = cursor.cursor_id

        # fetch
        try:
            raw_payload = self._rakuten.fetch_item_search_raw(
                cursor_type="recheck",
                item_code=item.external_item_code,
                page=page,
                hits=hits,
            )
        except RakutenItemSearchApiError as exc:
            self._repos.record_api_call(
                api_call_log_id=api_call_log_id,
                fetch_cursor_id=cursor_id,
                cursor_type="recheck",
                status="failed",
                page=page,
                error_code=exc.code,
            )
            # fetch_cursor §5.3 / §17.1 No.3: rate_limited（GRS-EXT-102）→ 同一処理内で paused
            if exc.code == "GRS-EXT-102" and cursor_id is not None:
                self._repos.update_cursor_progress(
                    cursor_id=cursor_id,
                    page=page,
                    cursor_status="paused",
                )
            raise

        # adapt (allow empty for recheck)
        try:
            adapted = adapt_item_search_raw_payload(
                raw_payload,
                cursor_type="recheck",
                page=page,
                allow_empty=True,
            )
        except RakutenItemSearchApiError as exc:
            self._repos.record_api_call(
                api_call_log_id=api_call_log_id,
                fetch_cursor_id=cursor_id,
                cursor_type="recheck",
                status="failed",
                page=page,
                error_code=exc.code,
            )
            raise

        self._repos.record_api_call(
            api_call_log_id=api_call_log_id,
            fetch_cursor_id=cursor_id,
            cursor_type="recheck",
            status="succeeded",
            page=page,
        )

        # raw_save（empty payload も含む）
        body = json.dumps(raw_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        object_key = build_item_search_raw_object_key(
            batch_run_id=job_run_id,
            api_call_log_id=api_call_log_id,
        )
        artifact = RawItemSearchArtifact(
            object_key=object_key,
            content_hash=content_hash_for_payload(body),
            api_call_log_id=api_call_log_id,
            cursor_id=cursor_id,
            cursor_type="recheck",
            page=page,
            body=body,
        )
        saved = self._repos.save_raw(artifact)
        if saved:
            result.raw_save_success_count += 1

        raw_meta = self._repos.raw_metadata.get(object_key, {})
        raw_metadata_id = (
            str(raw_meta["raw_metadata_id"]) if raw_meta.get("raw_metadata_id") else None
        )

        # resolve (IF-020)
        resolved = resolve_active_status_candidate(
            batch_run_id=job_run_id,
            external_item_code=item.external_item_code,
            candidates=adapted.candidates,
            item_id=item.item_id,
            raw_metadata_id=raw_metadata_id,
            api_call_log_id=api_call_log_id,
            source=item.source or SOURCE_RAKUTEN,
        )
        self._repos.upsert_candidate(resolved)
        result.candidate_upsert_count += 1
        if resolved.detection_basis == "empty_hit":
            result.empty_hit_count += 1
        elif resolved.detection_basis == "availability":
            result.availability_zero_count += 1

        # cursor_update: successful API path (including empty hit) → exhausted/completed
        if cursor_id is not None:
            self._repos.update_cursor_progress(
                cursor_id=cursor_id,
                page=page + 1,
                cursor_status="exhausted",
            )

    def _phase_finalize(self, result: ItemRecheckSyncResult) -> ItemRecheckSyncResult:
        if result.failed_item_codes and result.succeeded_item_codes:
            result.status = "partially_succeeded"
            if "GRS-BAT-002" not in result.error_codes:
                result.error_codes.append("GRS-BAT-002")
            tracker_status = "partially_succeeded"
        elif result.failed_item_codes and not result.succeeded_item_codes:
            result.status = "failed"
            if "GRS-BAT-001" not in result.error_codes:
                result.error_codes.append("GRS-BAT-001")
            tracker_status = "failed"
        else:
            result.status = "succeeded"
            tracker_status = "succeeded"

        self._tracker.complete(
            batch_id=BATCH_ID,
            job_run_id=result.job_run_id,
            status=tracker_status,
        )
        self._repos.record_phase(phase="finalize", status=result.status)
        result.completed_phases.append("finalize")
        return result
