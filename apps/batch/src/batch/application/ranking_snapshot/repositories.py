"""In-memory repositories used by BATCH-002 unit tests / scaffold wiring.

Production will replace these with real DB / Object Storage adapters while
keeping the same upsert / get-or-create semantics.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from batch.application.observability import (
    ApiCallLogWriter,
    ErrorLogWriter,
    PhaseLogWriter,
)
from batch.application.observability.binding import emit_api_call, emit_error, emit_phase
from batch.application.ranking_snapshot.idempotency import SOURCE_API_RANKING, SOURCE_RAKUTEN
from batch.application.ranking_snapshot.models import (
    PopularitySignalRow,
    RankingSnapshotHeader,
    RawRankingArtifact,
    StagingRankingRow,
    UnknownItemCandidate,
)
from batch.infrastructure.db import DatabaseError, DbReader, DbWriter
from batch.infrastructure.object_storage import ObjectRef, ObjectStorageClient


def _as_bigint(value: str | int | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _is_unique_violation(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "duplicate key" in text or "unique constraint" in text or "uq_" in text



def _parse_last_build_date(value: str) -> datetime:
    """Parse Rakuten ``lastBuildDate`` (RFC 2822) to aware datetime."""

    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return datetime.now(UTC)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _item_count_from_raw_body(body: bytes) -> int:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        return 0
    if not isinstance(payload, dict):
        return 0
    items = payload.get("Items")
    return len(items) if isinstance(items, list) else 0


def _looks_like_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return False
    return True


@dataclass
class RankingSnapshotRepositories:
    """Facade that persists Raw / Staging / Snapshot / signal / unknown via infrastructure."""

    object_storage: ObjectStorageClient
    db_writer: DbWriter
    bucket: str
    db_reader: DbReader | None = None
    # Item 突合の模擬。未解決は item_id=None + unknown 候補（Item 正本は作らない）
    known_item_codes: set[str] = field(default_factory=set)
    raw_metadata: dict[str, dict[str, object]] = field(default_factory=dict)
    staging_rankings: dict[tuple[object, ...], StagingRankingRow] = field(default_factory=dict)
    snapshots: dict[tuple[object, ...], RankingSnapshotHeader] = field(default_factory=dict)
    popularity_signals: dict[tuple[object, ...], PopularitySignalRow] = field(default_factory=dict)
    unknown_items: dict[str, UnknownItemCandidate] = field(default_factory=dict)
    created_items: list[object] = field(default_factory=list)
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

    def save_raw(self, artifact: RawRankingArtifact) -> str:
        """Persist Raw. Returns ``raw_metadata_id`` for staging linkage."""

        ref = ObjectRef(bucket=self.bucket, key=artifact.object_key)
        existing_meta = self.raw_metadata.get(artifact.object_key)
        if (
            existing_meta is not None
            and existing_meta.get("content_hash") == artifact.content_hash
            and existing_meta.get("import_status") in {"raw_saved", "staged", "imported"}
        ):
            raw_metadata_id = str(existing_meta.get("raw_metadata_id") or uuid.uuid4())
            self.raw_metadata[artifact.object_key] = {
                **existing_meta,
                "raw_metadata_id": raw_metadata_id,
                "import_status": existing_meta.get("import_status", "raw_saved"),
                "api_call_log_id": artifact.api_call_log_id,
                "genre_id": artifact.genre_id,
                "period": artifact.period,
                "page": artifact.page,
                "source": SOURCE_RAKUTEN,
                "source_api": SOURCE_API_RANKING,
            }
            return raw_metadata_id

        self.object_storage.put_object(
            ref,
            body=artifact.body,
            content_type="application/json",
        )
        raw_metadata_id = str(uuid.uuid4())
        fetched_at = datetime.now(UTC)
        item_count = _item_count_from_raw_body(artifact.body)
        self.raw_metadata[artifact.object_key] = {
            "raw_metadata_id": raw_metadata_id,
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
            (
                {
                    "raw_metadata_id": raw_metadata_id,
                    "api_call_log_id": artifact.api_call_log_id,
                    "object_key": artifact.object_key,
                    "source": SOURCE_RAKUTEN,
                    "source_api": SOURCE_API_RANKING,
                    "content_hash": artifact.content_hash,
                    "item_count": item_count,
                    "import_status": "raw_saved",
                    "fetched_at": fetched_at,
                },
            ),
        )
        return raw_metadata_id

    def get_or_create_snapshot(self, header: RankingSnapshotHeader) -> RankingSnapshotHeader:
        key = header.idempotency_key
        existing = self.snapshots.get(key)
        if existing is not None:
            return existing

        loaded = self._load_existing_snapshot(header)
        if loaded is not None:
            self.snapshots[key] = loaded
            return loaded

        snapshot_id = header.ranking_snapshot_id or str(uuid.uuid4())
        created = RankingSnapshotHeader(
            source=header.source,
            external_genre_id=header.external_genre_id,
            period=header.period,
            last_build_date=header.last_build_date,
            ranking_snapshot_id=snapshot_id,
        )
        now = datetime.now(UTC)
        row = {
            "ranking_snapshot_id": snapshot_id,
            "source": created.source,
            "external_genre_id": _as_bigint(created.external_genre_id),
            "period": created.period,
            "last_build_date": _parse_last_build_date(created.last_build_date),
            "fetched_at": now,
            "batch_run_id": self._batch_run_id,
        }
        try:
            self.db_writer.write_rows("ranking_snapshot", (row,))
        except DatabaseError as exc:
            if not _is_unique_violation(exc):
                raise
            loaded = self._load_existing_snapshot(header)
            if loaded is None:
                raise
            self.snapshots[key] = loaded
            return loaded

        self.snapshots[key] = created
        return created

    def _load_existing_snapshot(
        self, header: RankingSnapshotHeader
    ) -> RankingSnapshotHeader | None:
        if self.db_reader is None:
            return None
        try:
            result = self.db_reader.fetch_rows(
                "ranking_snapshot",
                columns=(
                    "ranking_snapshot_id",
                    "source",
                    "external_genre_id",
                    "period",
                    "last_build_date",
                ),
                equals=(
                    ("source", header.source),
                    ("external_genre_id", _as_bigint(header.external_genre_id)),
                    ("period", header.period),
                    ("last_build_date", _parse_last_build_date(header.last_build_date)),
                ),
                limit=1,
            )
        except DatabaseError:
            return None
        if not result.rows:
            return None
        row = result.rows[0]
        return RankingSnapshotHeader(
            source=str(row.get("source") or header.source),
            external_genre_id=str(row.get("external_genre_id") or header.external_genre_id),
            period=str(row.get("period") or header.period),
            last_build_date=header.last_build_date,
            ranking_snapshot_id=str(row["ranking_snapshot_id"]),
        )

    def upsert_staging(self, row: StagingRankingRow, *, raw_metadata_id: str) -> None:
        key = row.idempotency_key
        self.staging_rankings[key] = row
        now = datetime.now(UTC)
        self.db_writer.upsert_rows(
            "staging_ranking_signal",
            (
                {
                    "raw_metadata_id": raw_metadata_id,
                    "external_item_code": row.external_item_code,
                    "external_genre_id": _as_bigint(row.external_genre_id),
                    "rank": row.rank,
                    "period": row.period,
                    "last_build_date": _parse_last_build_date(row.last_build_date),
                    "staged_at": now,
                },
            ),
            conflict_columns=("raw_metadata_id", "rank"),
            update_columns=(
                "external_item_code",
                "external_genre_id",
                "period",
                "last_build_date",
                "staged_at",
            ),
        )

    def upsert_popularity_signal(self, row: PopularitySignalRow) -> None:
        key = row.idempotency_key
        self.popularity_signals[key] = row
        now = datetime.now(UTC)
        # live DB の item_id は uuid。scaffold の "item:..." は書かない
        item_id = row.item_id
        if item_id is not None and not _looks_like_uuid(item_id):
            item_id = None
        last_build = (
            _parse_last_build_date(row.last_build_date) if row.last_build_date else now
        )
        self.db_writer.upsert_rows(
            "item_popularity_signal",
            (
                {
                    "ranking_snapshot_id": row.ranking_snapshot_id,
                    "item_id": item_id,
                    "external_item_code": row.external_item_code,
                    "external_genre_id": _as_bigint(row.external_genre_id),
                    "rank": row.rank,
                    "period": row.period,
                    "last_build_date": last_build,
                    "fetched_at": now,
                },
            ),
            conflict_columns=("ranking_snapshot_id", "rank"),
            update_columns=(
                "item_id",
                "external_item_code",
                "external_genre_id",
                "period",
                "last_build_date",
                "fetched_at",
            ),
        )

    def record_unknown_item(self, candidate: UnknownItemCandidate) -> None:
        # 1 itemCode = 1 cursor（仕様書 §18.1）。再実行時は上書き。
        self.unknown_items[candidate.external_item_code] = candidate
        cursor_id = str(uuid.uuid4())
        cursor_value = {
            "scope": {
                "external_item_code": candidate.external_item_code,
                "ranking_snapshot_id": candidate.ranking_snapshot_id,
                "rank": candidate.rank,
                "period": candidate.period,
            },
            "position": {"page": 1, "hits_per_page": 30},
        }
        insert_row = {
            "fetch_cursor_id": cursor_id,
            "source": SOURCE_RAKUTEN,
            "source_api": "item_search",
            "cursor_type": candidate.cursor_type,
            "target_external_genre_id": _as_bigint(candidate.external_genre_id),
            "cursor_status": "active",
            "cursor_value": cursor_value,
        }
        try:
            self.db_writer.write_rows("fetch_cursor", (insert_row,))
        except DatabaseError as exc:
            if not _is_unique_violation(exc):
                raise
            # 同一 scope の ranking_supplement は既存行を正とする（再smoke 冪等）
            return


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
