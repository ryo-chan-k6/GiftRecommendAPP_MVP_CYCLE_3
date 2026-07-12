"""BATCH-001 楽天ジャンル同期ジョブ実装.

処理 Phase（仕様書 §8.2）:
plan → fetch → adapt → raw_save → stage → upsert → finalize
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence

from batch.application.genre_sync.idempotency import SOURCE_RAKUTEN, build_genre_raw_object_key, content_hash_for_payload
from batch.application.genre_sync.models import (
    GenreFetchPlan,
    GenreRow,
    GenreSyncResult,
    RawGenreArtifact,
)
from batch.application.genre_sync.repositories import GenreSyncRepositories
from batch.application.job_run import JobRunTracker, ScaffoldJobRunTracker
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger
from batch.infrastructure.object_storage import ObjectStorageError
from batch.infrastructure.rakuten import (
    RakutenApiClient,
    RakutenGenreApiError,
    ScaffoldRakutenApiClient,
    adapt_genre_raw_payload,
)

BATCH_ID = "BATCH-001"
GENRE_SYNC_PHASES: tuple[str, ...] = (
    "plan",
    "fetch",
    "adapt",
    "raw_save",
    "stage",
    "upsert",
    "finalize",
)

# MVP placeholder fetch_plan（本番ジャンルIDは Human が設定投入）
DEFAULT_TARGET_GENRE_IDS: tuple[str, ...] = ("0",)


class GenreSyncJob:
    """Orchestrates BATCH-001 genre sync phases."""

    def __init__(
        self,
        *,
        rakuten_client: RakutenApiClient | None = None,
        repositories: GenreSyncRepositories,
        job_run_tracker: JobRunTracker | None = None,
        logger: BatchLogger | None = None,
    ) -> None:
        self._rakuten = rakuten_client or ScaffoldRakutenApiClient()
        self._repos = repositories
        self._tracker = job_run_tracker or ScaffoldJobRunTracker()
        self._logger = logger or ScaffoldBatchLogger()

    def run(
        self,
        *,
        job_run_id: str,
        target_genre_ids: Sequence[str] | None = None,
        trace_id: str | None = None,
    ) -> GenreSyncResult:
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        self._tracker.start(batch_id=BATCH_ID, job_run_id=job_run_id)

        result = GenreSyncResult(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")

        try:
            plan = self._phase_plan(target_genre_ids)
            result.planned_genre_ids = plan.target_genre_ids
            result.completed_phases.append("plan")
            self._repos.record_phase(phase="plan", status="succeeded")
            bound_logger.info("genre_sync.plan", genre_count=len(plan.target_genre_ids))

            if not plan.target_genre_ids:
                result.status = "failed"
                result.error_codes.append("GRS-BAT-001")
                self._repos.record_error(code="GRS-BAT-001", summary="empty fetch_plan")
                self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
                result.completed_phases.append("finalize")
                return result

            for genre_id in plan.target_genre_ids:
                try:
                    self._sync_one_genre(genre_id=genre_id, job_run_id=job_run_id, result=result)
                    result.succeeded_genre_ids.append(genre_id)
                except RakutenGenreApiError as exc:
                    result.failed_genre_ids.append(genre_id)
                    result.error_codes.append(exc.code)
                    self._repos.record_error(code=exc.code, summary=exc.message, genre_id=genre_id)
                    bound_logger.error(
                        "genre_sync.genre_failed",
                        genre_id=genre_id,
                        error_code=exc.code,
                    )
                except ObjectStorageError as exc:
                    result.failed_genre_ids.append(genre_id)
                    result.error_codes.append(exc.code)
                    self._repos.record_error(code=exc.code, summary=exc.message, genre_id=genre_id)
                    bound_logger.error(
                        "genre_sync.raw_save_failed",
                        genre_id=genre_id,
                        error_code=exc.code,
                    )
                except Exception as exc:  # noqa: BLE001 — finalize partial failure
                    result.failed_genre_ids.append(genre_id)
                    result.error_codes.append("GRS-BAT-001")
                    self._repos.record_error(
                        code="GRS-BAT-001",
                        summary=str(exc),
                        genre_id=genre_id,
                    )
                    bound_logger.error("genre_sync.unexpected_failure", genre_id=genre_id)

            for phase in ("fetch", "adapt", "raw_save", "stage", "upsert"):
                if phase not in result.completed_phases:
                    result.completed_phases.append(phase)

            result = self._phase_finalize(result)
            bound_logger.info(
                "genre_sync.finalize",
                status=result.status,
                succeeded=len(result.succeeded_genre_ids),
                failed=len(result.failed_genre_ids),
            )
            return result
        except Exception:
            self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
            raise

    def _phase_plan(self, target_genre_ids: Sequence[str] | None) -> GenreFetchPlan:
        if target_genre_ids is None or len(tuple(target_genre_ids)) == 0:
            resolved = DEFAULT_TARGET_GENRE_IDS
        else:
            resolved = tuple(str(g).strip() for g in target_genre_ids if str(g).strip())
        return GenreFetchPlan(source=SOURCE_RAKUTEN, target_genre_ids=resolved)

    def _sync_one_genre(self, *, genre_id: str, job_run_id: str, result: GenreSyncResult) -> None:
        api_call_log_id = f"api_{uuid.uuid4().hex[:12]}"

        # fetch
        try:
            raw_payload = self._rakuten.fetch_genre_raw(genre_id=genre_id)
        except RakutenGenreApiError as exc:
            self._repos.record_api_call(
                api_call_log_id=api_call_log_id,
                genre_id=genre_id,
                status="failed",
                error_code=exc.code,
            )
            raise

        self._repos.record_api_call(
            api_call_log_id=api_call_log_id,
            genre_id=genre_id,
            status="succeeded",
        )

        # adapt
        genre = adapt_genre_raw_payload(raw_payload, requested_genre_id=genre_id)

        # raw_save
        body = json.dumps(raw_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        object_key = build_genre_raw_object_key(
            batch_run_id=job_run_id,
            api_call_log_id=api_call_log_id,
        )
        artifact = RawGenreArtifact(
            object_key=object_key,
            content_hash=content_hash_for_payload(body),
            api_call_log_id=api_call_log_id,
            genre_id=genre.genre_id,
            body=body,
        )
        self._repos.save_raw(artifact)

        # stage + upsert（本 Batch 内完結: 仕様書 §18 No.2 基本案）
        row = GenreRow(
            source=SOURCE_RAKUTEN,
            external_genre_id=genre.genre_id,
            genre_name=genre.genre_name,
            parent_external_genre_id=genre.parent_genre_id,
            genre_level=genre.genre_level,
        )
        self._repos.upsert_staging(row)
        self._repos.upsert_external(row)
        result.upserted_external_genre_count += 1

        meta = self._repos.raw_metadata.get(object_key)
        if meta is not None:
            meta["import_status"] = "staged"

    def _phase_finalize(self, result: GenreSyncResult) -> GenreSyncResult:
        if result.failed_genre_ids and result.succeeded_genre_ids:
            result.status = "partially_succeeded"
            if "GRS-BAT-002" not in result.error_codes:
                result.error_codes.append("GRS-BAT-002")
            tracker_status = "partially_succeeded"
        elif result.failed_genre_ids and not result.succeeded_genre_ids:
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
