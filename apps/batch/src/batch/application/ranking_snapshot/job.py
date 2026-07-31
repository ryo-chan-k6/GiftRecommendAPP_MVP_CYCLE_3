"""BATCH-002 楽天ランキングスナップショット取得ジョブ実装.

処理 Phase（仕様書 §8.2）:
plan → fetch → adapt → raw_save → stage → snapshot → upsert → unknown → finalize
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence

from batch.application.job_run import JobRunTracker, ScaffoldJobRunTracker
from batch.application.ranking_snapshot.idempotency import (
    SOURCE_RAKUTEN,
    build_ranking_raw_object_key,
    content_hash_for_payload,
)
from batch.application.ranking_snapshot.models import (
    PopularitySignalRow,
    RankingFetchPlan,
    RankingSnapshotHeader,
    RankingSyncResult,
    RawRankingArtifact,
    StagingRankingRow,
    UnknownItemCandidate,
)
from batch.application.ranking_snapshot.repositories import RankingSnapshotRepositories
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger
from batch.infrastructure.object_storage import ObjectStorageError
from batch.infrastructure.rakuten import (
    RakutenApiClient,
    RakutenRankingApiError,
    ScaffoldRakutenApiClient,
    adapt_ranking_raw_payload,
)

BATCH_ID = "BATCH-002"
RANKING_SNAPSHOT_PHASES: tuple[str, ...] = (
    "plan",
    "fetch",
    "adapt",
    "raw_save",
    "stage",
    "snapshot",
    "upsert",
    "unknown",
    "finalize",
)

# MVP placeholder fetch_plan（本番ジャンルID / period は Human が設定投入）
DEFAULT_TARGET_GENRE_IDS: tuple[str, ...] = ("100",)
DEFAULT_PERIOD = "daily"
DEFAULT_MAX_PAGES = 1


class RankingSnapshotJob:
    """Orchestrates BATCH-002 ranking snapshot phases."""

    def __init__(
        self,
        *,
        rakuten_client: RakutenApiClient | None = None,
        repositories: RankingSnapshotRepositories,
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
        target_genre_ids: Sequence[str] | None = None,
        period: str | None = None,
        max_pages: int | None = None,
        trace_id: str | None = None,
    ) -> RankingSyncResult:
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        self._tracker.start(batch_id=BATCH_ID, job_run_id=job_run_id)

        result = RankingSyncResult(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")

        try:
            plan = self._phase_plan(
                target_genre_ids=target_genre_ids,
                period=period,
                max_pages=max_pages,
            )
            result.planned_genre_ids = plan.target_genre_ids
            result.period = plan.period
            result.completed_phases.append("plan")
            self._repos.record_phase(phase="plan", status="succeeded")
            bound_logger.info(
                "ranking_snapshot.plan",
                genre_count=len(plan.target_genre_ids),
                period=plan.period,
            )

            if not plan.target_genre_ids:
                result.status = "failed"
                result.error_codes.append("GRS-BAT-001")
                self._repos.record_error(code="GRS-BAT-001", summary="empty fetch_plan")
                self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
                result.completed_phases.append("finalize")
                return result

            for genre_id in plan.target_genre_ids:
                try:
                    self._sync_one_genre(
                        genre_id=genre_id,
                        period=plan.period,
                        max_pages=plan.max_pages,
                        job_run_id=job_run_id,
                        result=result,
                    )
                    result.succeeded_genre_ids.append(genre_id)
                except RakutenRankingApiError as exc:
                    result.failed_genre_ids.append(genre_id)
                    result.error_codes.append(exc.code)
                    self._repos.record_error(code=exc.code, summary=exc.message, genre_id=genre_id)
                    bound_logger.error(
                        "ranking_snapshot.genre_failed",
                        genre_id=genre_id,
                        error_code=exc.code,
                    )
                except ObjectStorageError as exc:
                    result.failed_genre_ids.append(genre_id)
                    result.error_codes.append(exc.code)
                    self._repos.record_error(code=exc.code, summary=exc.message, genre_id=genre_id)
                    bound_logger.error(
                        "ranking_snapshot.raw_save_failed",
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
                    bound_logger.error("ranking_snapshot.unexpected_failure", genre_id=genre_id)

            for phase in ("fetch", "adapt", "raw_save", "stage", "snapshot", "upsert", "unknown"):
                if phase not in result.completed_phases:
                    result.completed_phases.append(phase)

            result = self._phase_finalize(result)
            bound_logger.info(
                "ranking_snapshot.finalize",
                status=result.status,
                succeeded=len(result.succeeded_genre_ids),
                failed=len(result.failed_genre_ids),
            )
            return result
        except Exception:
            self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
            raise

    def _phase_plan(
        self,
        *,
        target_genre_ids: Sequence[str] | None,
        period: str | None,
        max_pages: int | None,
    ) -> RankingFetchPlan:
        if target_genre_ids is None or len(tuple(target_genre_ids)) == 0:
            resolved = DEFAULT_TARGET_GENRE_IDS
        else:
            resolved = tuple(str(g).strip() for g in target_genre_ids if str(g).strip())

        resolved_period = (period or DEFAULT_PERIOD).strip() or DEFAULT_PERIOD
        resolved_pages = DEFAULT_MAX_PAGES if max_pages is None else max(1, int(max_pages))
        return RankingFetchPlan(
            source=SOURCE_RAKUTEN,
            target_genre_ids=resolved,
            period=resolved_period,
            max_pages=resolved_pages,
        )

    def _sync_one_genre(
        self,
        *,
        genre_id: str,
        period: str,
        max_pages: int,
        job_run_id: str,
        result: RankingSyncResult,
    ) -> None:
        # MVP scaffold: max_pages まで page 単位で取得し、同一 genre 内で結合反映する
        for page in range(1, max_pages + 1):
            self._sync_one_page(
                genre_id=genre_id,
                period=period,
                page=page,
                job_run_id=job_run_id,
                result=result,
            )

    def _sync_one_page(
        self,
        *,
        genre_id: str,
        period: str,
        page: int,
        job_run_id: str,
        result: RankingSyncResult,
    ) -> None:
        api_call_log_id = str(uuid.uuid4())

        # fetch
        try:
            raw_payload = self._rakuten.fetch_ranking_raw(
                genre_id=genre_id,
                period=period,
                page=page,
            )
        except RakutenRankingApiError as exc:
            self._repos.record_api_call(
                api_call_log_id=api_call_log_id,
                genre_id=genre_id,
                period=period,
                page=page,
                status="failed",
                error_code=exc.code,
            )
            raise

        # adapt
        try:
            adapted = adapt_ranking_raw_payload(
                raw_payload,
                requested_genre_id=genre_id,
                period=period,
            )
        except RakutenRankingApiError as exc:
            self._repos.record_api_call(
                api_call_log_id=api_call_log_id,
                genre_id=genre_id,
                period=period,
                page=page,
                status="failed",
                error_code=exc.code,
            )
            raise

        self._repos.record_api_call(
            api_call_log_id=api_call_log_id,
            genre_id=genre_id,
            period=period,
            page=page,
            status="succeeded",
        )

        # raw_save
        body = json.dumps(raw_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        object_key = build_ranking_raw_object_key(
            batch_run_id=job_run_id,
            api_call_log_id=api_call_log_id,
        )
        artifact = RawRankingArtifact(
            object_key=object_key,
            content_hash=content_hash_for_payload(body),
            api_call_log_id=api_call_log_id,
            genre_id=genre_id,
            period=period,
            page=page,
            body=body,
        )
        raw_metadata_id = self._repos.save_raw(artifact)

        # stage
        for entry in adapted.entries:
            staging = StagingRankingRow(
                source=SOURCE_RAKUTEN,
                external_genre_id=genre_id,
                period=period,
                last_build_date=adapted.last_build_date,
                rank=entry.rank,
                external_item_code=entry.item_code,
            )
            self._repos.upsert_staging(staging, raw_metadata_id=raw_metadata_id)

        meta = self._repos.raw_metadata.get(object_key)
        if meta is not None:
            meta["import_status"] = "staged"

        # snapshot (get-or-create)
        snapshot = self._repos.get_or_create_snapshot(
            RankingSnapshotHeader(
                source=SOURCE_RAKUTEN,
                external_genre_id=genre_id,
                period=period,
                last_build_date=adapted.last_build_date,
            )
        )
        assert snapshot.ranking_snapshot_id is not None
        result.snapshot_count = len(self._repos.snapshots)

        # upsert popularity signals + unknown candidates
        for entry in adapted.entries:
            item_id = self._repos.resolve_item_id(entry.item_code)
            signal = PopularitySignalRow(
                ranking_snapshot_id=snapshot.ranking_snapshot_id,
                rank=entry.rank,
                external_item_code=entry.item_code,
                item_id=item_id,
                external_genre_id=genre_id,
                period=period,
                last_build_date=adapted.last_build_date,
            )
            self._repos.upsert_popularity_signal(signal)
            result.popularity_signal_upsert_count = len(self._repos.popularity_signals)

            if item_id is None:
                self._repos.record_unknown_item(
                    UnknownItemCandidate(
                        external_item_code=entry.item_code,
                        external_genre_id=genre_id,
                        period=period,
                        ranking_snapshot_id=snapshot.ranking_snapshot_id,
                        rank=entry.rank,
                    )
                )
        result.unknown_item_count = len(self._repos.unknown_items)

    def _phase_finalize(self, result: RankingSyncResult) -> RankingSyncResult:
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
