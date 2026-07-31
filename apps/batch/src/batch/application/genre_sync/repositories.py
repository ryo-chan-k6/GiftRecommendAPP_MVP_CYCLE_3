"""In-memory repositories used by BATCH-001 unit tests / scaffold wiring.

Production will replace these with real DB / Object Storage adapters while
keeping the same upsert semantics (source + external_genre_id).

Wave 2: optional ``phase_log_writer`` / ``error_log_writer`` bind to Postgres
via ``bind_run`` (app phase → DDL phase_name mapping for plan/finalize only).

Wave 3: optional ``api_call_log_writer`` writes ``api_call_log`` (source_api=genre_search).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from batch.application.genre_sync.idempotency import SOURCE_API_GENRE, SOURCE_RAKUTEN
from batch.application.genre_sync.models import GenreRow, RawGenreArtifact
from batch.application.observability import (
    ApiCallLogWriter,
    ErrorLogWriter,
    PhaseLogWriter,
    map_app_phase_status,
    map_app_phase_to_ddl,
)
from batch.application.observability.mapping import warn_unmapped_app_phase
from batch.infrastructure.db import DbWriter
from batch.infrastructure.object_storage import ObjectRef, ObjectStorageClient

# DDL api_call_log / raw_product_metadata.source_api（object_key 用 SOURCE_API_GENRE="genre" とは別）
_DDL_SOURCE_API_GENRE_SEARCH = "genre_search"


def _as_bigint(value: str | None) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.lstrip("-").isdigit():
        return int(text)
    return None


@dataclass
class GenreSyncRepositories:
    """Facade that persists Raw / Staging / external_genre via infrastructure protocols."""

    object_storage: ObjectStorageClient
    db_writer: DbWriter
    bucket: str
    raw_metadata: dict[str, dict[str, object]] = field(default_factory=dict)
    staging_genres: dict[tuple[str, str], GenreRow] = field(default_factory=dict)
    external_genres: dict[tuple[str, str], GenreRow] = field(default_factory=dict)
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

    def save_raw(self, artifact: RawGenreArtifact) -> str:
        """Persist Raw. Returns ``raw_metadata_id`` for staging linkage."""

        ref = ObjectRef(bucket=self.bucket, key=artifact.object_key)
        existing_meta = self.raw_metadata.get(artifact.object_key)
        if (
            existing_meta is not None
            and existing_meta.get("content_hash") == artifact.content_hash
            and existing_meta.get("import_status") in {"raw_saved", "staged", "imported"}
        ):
            # Same content_hash: skip Object Storage rewrite (仕様書 §11)
            raw_metadata_id = str(existing_meta.get("raw_metadata_id") or uuid.uuid4())
            self.raw_metadata[artifact.object_key] = {
                **existing_meta,
                "raw_metadata_id": raw_metadata_id,
                "import_status": existing_meta.get("import_status", "raw_saved"),
                "api_call_log_id": artifact.api_call_log_id,
                "genre_id": artifact.genre_id,
                "source": SOURCE_RAKUTEN,
                "source_api": SOURCE_API_GENRE,
            }
            return raw_metadata_id

        self.object_storage.put_object(
            ref,
            body=artifact.body,
            content_type="application/json",
        )
        raw_metadata_id = str(uuid.uuid4())
        fetched_at = datetime.now(UTC)
        self.raw_metadata[artifact.object_key] = {
            "raw_metadata_id": raw_metadata_id,
            "object_key": artifact.object_key,
            "content_hash": artifact.content_hash,
            "api_call_log_id": artifact.api_call_log_id,
            "genre_id": artifact.genre_id,
            "source": SOURCE_RAKUTEN,
            "source_api": SOURCE_API_GENRE,
            "import_status": "raw_saved",
        }
        # DDL 列のみ INSERT（genre_id はアプリ内メタ。DB には持たない）
        self.db_writer.write_rows(
            "raw_product_metadata",
            (
                {
                    "raw_metadata_id": raw_metadata_id,
                    "api_call_log_id": artifact.api_call_log_id,
                    "object_key": artifact.object_key,
                    "source": SOURCE_RAKUTEN,
                    "source_api": _DDL_SOURCE_API_GENRE_SEARCH,
                    "content_hash": artifact.content_hash,
                    "item_count": 0,
                    "import_status": "raw_saved",
                    "fetched_at": fetched_at,
                },
            ),
        )
        return raw_metadata_id

    def upsert_staging(self, row: GenreRow, *, raw_metadata_id: str) -> None:
        key = row.idempotency_key
        self.staging_genres[key] = row
        now = datetime.now(UTC)
        self.db_writer.write_rows(
            "staging_genre",
            (
                {
                    "raw_metadata_id": raw_metadata_id,
                    "source": row.source,
                    "external_genre_id": _as_bigint(row.external_genre_id),
                    "genre_name": row.genre_name,
                    "parent_external_genre_id": _as_bigint(row.parent_external_genre_id),
                    "genre_level": row.genre_level if row.genre_level is not None else 0,
                    "is_leaf": row.is_leaf,
                    "staged_at": now,
                },
            ),
        )

    def upsert_external(self, row: GenreRow) -> None:
        # Idempotency: source + external_genre_id (仕様書 §11)
        key = row.idempotency_key
        self.external_genres[key] = row
        now = datetime.now(UTC)
        self.db_writer.upsert_rows(
            "external_genre",
            (
                {
                    "source": row.source,
                    "external_genre_id": _as_bigint(row.external_genre_id),
                    "genre_name": row.genre_name,
                    "parent_external_genre_id": _as_bigint(row.parent_external_genre_id),
                    "genre_level": row.genre_level if row.genre_level is not None else 0,
                    "is_leaf": row.is_leaf,
                    "fetched_at": now,
                },
            ),
            conflict_columns=("external_genre_id",),
            update_columns=(
                "source",
                "genre_name",
                "parent_external_genre_id",
                "genre_level",
                "is_leaf",
                "fetched_at",
            ),
        )

    def record_api_call(
        self,
        *,
        api_call_log_id: str,
        genre_id: str,
        status: str,
        error_code: str | None = None,
    ) -> None:
        self.api_call_logs.append(
            {
                "api_call_log_id": api_call_log_id,
                "genre_id": genre_id,
                "status": status,
                "error_code": error_code,
                # Never log Authorization / access keys
            }
        )
        writer = self.api_call_log_writer
        batch_run_id = self._batch_run_id
        if writer is None or batch_run_id is None:
            return
        writer.record_call(
            api_call_log_id=api_call_log_id,
            batch_run_id=batch_run_id,
            source_api=_DDL_SOURCE_API_GENRE_SEARCH,
            call_status=status,
            request_params_json={"genre_id": genre_id},
            error_code=error_code,
            trace_id=self._trace_id,
        )

    def record_error(self, *, code: str, summary: str, genre_id: str | None = None) -> None:
        self.error_logs.append(
            {
                "code": code,
                "summary": summary,
                "genre_id": genre_id,
            }
        )
        writer = self.error_log_writer
        batch_run_id = self._batch_run_id
        if writer is None or batch_run_id is None:
            return
        detail: dict[str, object] = {}
        if genre_id is not None:
            detail["genre_id"] = genre_id
        writer.record_error(
            batch_run_id=batch_run_id,
            error_code=code,
            error_message=summary,
            detail=detail or None,
            trace_id=self._trace_id,
        )

    def record_phase(self, *, phase: str, status: str) -> None:
        self.phase_logs.append({"phase": phase, "status": status})
        writer = self.phase_log_writer
        batch_run_id = self._batch_run_id
        if writer is None or batch_run_id is None:
            return
        ddl_phase = map_app_phase_to_ddl(phase)
        if ddl_phase is None:
            warn_unmapped_app_phase(phase)
            return
        writer.record_phase(
            batch_run_id=batch_run_id,
            phase_name=ddl_phase,
            phase_status=map_app_phase_status(status),
            app_phase=phase,
            trace_id=self._trace_id,
        )
