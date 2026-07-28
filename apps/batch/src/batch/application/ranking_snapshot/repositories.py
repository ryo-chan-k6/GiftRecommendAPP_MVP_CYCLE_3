"""In-memory repositories used by BATCH-002 unit tests / scaffold wiring.

Production will replace these with real DB / Object Storage adapters while
keeping the same upsert / get-or-create semantics.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from batch.application.ranking_snapshot.idempotency import SOURCE_API_RANKING, SOURCE_RAKUTEN
from batch.application.ranking_snapshot.models import (
    PopularitySignalRow,
    RankingSnapshotHeader,
    RawRankingArtifact,
    StagingRankingRow,
    UnknownItemCandidate,
)
from batch.infrastructure.db import DbWriter
from batch.infrastructure.object_storage import ObjectRef, ObjectStorageClient


from batch.application.observability import (
    ApiCallLogWriter,
    ErrorLogWriter,
    PhaseLogWriter,
)
from batch.application.observability.binding import emit_api_call, emit_error, emit_phase

@dataclass
class RankingSnapshotRepositories:
    """Facade that persists Raw / Staging / Snapshot / signal / unknown via infrastructure."""

    object_storage: ObjectStorageClient
    db_writer: DbWriter
    bucket: str
    # Item 突合の模擬。未解決は item_id=None + unknown 候補（Item 正本は作らない）
    known_item_codes: set[str] = field(default_factory=set)
    raw_metadata: dict[str, dict[str, object]] = field(default_factory=dict)
    staging_rankings: dict[tuple[str, str, str, str, int], StagingRankingRow] = field(
        default_factory=dict
    )
    snapshots: dict[tuple[str, str, str, str], RankingSnapshotHeader] = field(default_factory=dict)
    popularity_signals: dict[tuple[str, int], PopularitySignalRow] = field(default_factory=dict)
    unknown_items: dict[str, UnknownItemCandidate] = field(default_factory=dict)
    # Item 正本を作らないことを検証するため、誤って作成したものを追跡する
    created_items: list[dict[str, object]] = field(default_factory=list)
    api_call_logs: list[dict[str, object]] = field(default_factory=list)
    error_logs: list[dict[str, object]] = field(default_factory=list)
    phase_logs: list[dict[str, object]] = field(default_factory=list)
    phase_log_writer: PhaseLogWriter | None = None
    error_log_writer: ErrorLogWriter | None = None
    api_call_log_writer: ApiCallLogWriter | None = None
    _batch_run_id: str | None = field(default=None, repr=False)
    _trace_id: str | None = field(default=None, repr=False)


    def bind_run(self, *, batch_run_id: str, trace_id: str | None = None) -> None:
        """Bind ``batch_run_id`` (= job_run_id UUID) for observability DB writes."""

        self._batch_run_id = batch_run_id
        self._trace_id = trace_id

    def resolve_item_id(self, external_item_code: str) -> str | None:
        """Resolve item_id from known_item_codes. Does not create Item 正本."""

        if external_item_code in self.known_item_codes:
            return f"item:{external_item_code}"
        return None

    def save_raw(self, artifact: RawRankingArtifact) -> None:
        ref = ObjectRef(bucket=self.bucket, key=artifact.object_key)
        existing_meta = self.raw_metadata.get(artifact.object_key)
        if (
            existing_meta is not None
            and existing_meta.get("content_hash") == artifact.content_hash
            and existing_meta.get("import_status") in {"raw_saved", "staged", "imported"}
        ):
            self.raw_metadata[artifact.object_key] = {
                **existing_meta,
                "import_status": existing_meta.get("import_status", "raw_saved"),
                "api_call_log_id": artifact.api_call_log_id,
                "genre_id": artifact.genre_id,
                "period": artifact.period,
                "page": artifact.page,
                "source": SOURCE_RAKUTEN,
                "source_api": SOURCE_API_RANKING,
            }
            return

        self.object_storage.put_object(
            ref,
            body=artifact.body,
            content_type="application/json",
        )
        self.raw_metadata[artifact.object_key] = {
            "object_key": artifact.object_key,
            "content_hash": artifact.content_hash,
            "api_call_log_id": artifact.api_call_log_id,
            "genre_id": artifact.genre_id,
            "period": artifact.period,
            "page": artifact.page,
            "source": SOURCE_RAKUTEN,
            "source_api": SOURCE_API_RANKING,
            "import_status": "raw_saved",
        }
        self.db_writer.write_rows(
            "raw_product_metadata",
            (dict(self.raw_metadata[artifact.object_key]),),
        )

    def upsert_staging(self, row: StagingRankingRow) -> None:
        key = row.idempotency_key
        self.staging_rankings[key] = row
        self.db_writer.write_rows(
            "staging_ranking_signal",
            (
                {
                    "source": row.source,
                    "external_genre_id": row.external_genre_id,
                    "period": row.period,
                    "last_build_date": row.last_build_date,
                    "rank": row.rank,
                    "external_item_code": row.external_item_code,
                },
            ),
        )

    def get_or_create_snapshot(self, header: RankingSnapshotHeader) -> RankingSnapshotHeader:
        key = header.idempotency_key
        existing = self.snapshots.get(key)
        if existing is not None:
            return existing

        snapshot_id = header.ranking_snapshot_id or f"rs_{uuid.uuid4().hex[:12]}"
        created = RankingSnapshotHeader(
            source=header.source,
            external_genre_id=header.external_genre_id,
            period=header.period,
            last_build_date=header.last_build_date,
            ranking_snapshot_id=snapshot_id,
        )
        self.snapshots[key] = created
        self.db_writer.write_rows(
            "ranking_snapshot",
            (
                {
                    "ranking_snapshot_id": snapshot_id,
                    "source": created.source,
                    "external_genre_id": created.external_genre_id,
                    "period": created.period,
                    "last_build_date": created.last_build_date,
                },
            ),
        )
        return created

    def upsert_popularity_signal(self, row: PopularitySignalRow) -> None:
        key = row.idempotency_key
        self.popularity_signals[key] = row
        self.db_writer.write_rows(
            "item_popularity_signal",
            (
                {
                    "ranking_snapshot_id": row.ranking_snapshot_id,
                    "rank": row.rank,
                    "external_item_code": row.external_item_code,
                    "item_id": row.item_id,
                    "external_genre_id": row.external_genre_id,
                    "period": row.period,
                },
            ),
        )

    def record_unknown_item(self, candidate: UnknownItemCandidate) -> None:
        # 1 itemCode = 1 cursor（仕様書 §18.1）。再実行時は上書き。
        self.unknown_items[candidate.external_item_code] = candidate
        self.db_writer.write_rows(
            "fetch_cursor",
            (
                {
                    "cursor_type": candidate.cursor_type,
                    "external_item_code": candidate.external_item_code,
                    "external_genre_id": candidate.external_genre_id,
                    "period": candidate.period,
                    "ranking_snapshot_id": candidate.ranking_snapshot_id,
                    "rank": candidate.rank,
                },
            ),
        )

    def record_api_call(
        self,
        *,
        api_call_log_id: str,
        genre_id: str,
        status: str,
        period: str | None = None,
        page: int | None = None,
        error_code: str | None = None,
    ) -> None:
        params: dict[str, object] = {"genre_id": genre_id}
        if period is not None:
            params["period"] = period
        if page is not None:
            params["page"] = page
        emit_api_call(
            api_call_logs=self.api_call_logs,
            api_call_log_writer=self.api_call_log_writer,
            batch_run_id=self._batch_run_id,
            trace_id=self._trace_id,
            api_call_log_id=api_call_log_id,
            source_api="item_ranking",
            call_status=status,
            memory_entry={
                "api_call_log_id": api_call_log_id,
                "genre_id": genre_id,
                "period": period,
                "page": page,
                "status": status,
                "error_code": error_code,
            },
            request_params_json=params,
            error_code=error_code,
        )

    def record_error(self, *, code: str, summary: str, genre_id: str | None = None) -> None:
        detail: dict[str, object] = {}
        if genre_id is not None:
            detail["genre_id"] = genre_id
        emit_error(
            error_logs=self.error_logs,
            error_log_writer=self.error_log_writer,
            batch_run_id=self._batch_run_id,
            trace_id=self._trace_id,
            code=code,
            summary=summary,
            memory_extra={"genre_id": genre_id},
            detail=detail or None,
        )

    def record_phase(self, *, phase: str, status: str) -> None:
        emit_phase(
            phase_logs=self.phase_logs,
            phase_log_writer=self.phase_log_writer,
            batch_run_id=self._batch_run_id,
            trace_id=self._trace_id,
            phase=phase,
            status=status,
        )
