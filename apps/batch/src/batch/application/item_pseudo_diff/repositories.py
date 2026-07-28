"""In-memory repositories for BATCH-003 unit tests / scaffold wiring.

Production will replace these with real DB / Object Storage adapters while
keeping the same Raw / fetch_cursor semantics. Item / Staging は更新しない。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from batch.application.item_pseudo_diff.idempotency import (
    SOURCE_API_ITEM_SEARCH,
    SOURCE_RAKUTEN,
    cursor_scope_fingerprint,
)
from batch.application.item_pseudo_diff.models import FetchCursorRow, RawItemSearchArtifact
from batch.infrastructure.db import DbWriter
from batch.infrastructure.object_storage import ObjectRef, ObjectStorageClient


from batch.application.observability import (
    ApiCallLogWriter,
    ErrorLogWriter,
    PhaseLogWriter,
)
from batch.application.observability.binding import emit_api_call, emit_error, emit_phase

@dataclass
class ItemPseudoDiffRepositories:
    """Facade that persists Raw / fetch_cursor / logs via infrastructure."""

    object_storage: ObjectStorageClient
    db_writer: DbWriter
    bucket: str
    # 事前投入された active カーソル（BATCH-002 ranking_supplement 等）
    seed_cursors: list[FetchCursorRow] = field(default_factory=list)
    fetch_cursors: dict[str, FetchCursorRow] = field(default_factory=dict)
    raw_metadata: dict[str, dict[str, object]] = field(default_factory=dict)
    # 境界検証: Item / Staging を誤って作った場合に検知する
    created_items: list[dict[str, object]] = field(default_factory=list)
    created_staging: list[dict[str, object]] = field(default_factory=list)
    api_call_logs: list[dict[str, object]] = field(default_factory=list)
    error_logs: list[dict[str, object]] = field(default_factory=list)
    phase_logs: list[dict[str, object]] = field(default_factory=list)
    phase_log_writer: PhaseLogWriter | None = None
    error_log_writer: ErrorLogWriter | None = None
    api_call_log_writer: ApiCallLogWriter | None = None
    _batch_run_id: str | None = field(default=None, repr=False)
    _trace_id: str | None = field(default=None, repr=False)


    def bind_run(self, *, batch_run_id: str, trace_id: str | None = None) -> None:
        """Bind shared pipeline ``batch_run_id`` for observability DB writes."""

        self._batch_run_id = batch_run_id
        self._trace_id = trace_id

    def list_active_cursors(self) -> list[FetchCursorRow]:
        """Return active seed + stored cursors (recheck は含めない)."""

        rows: list[FetchCursorRow] = []
        for row in self.seed_cursors:
            # recheck は BATCH-004。本 Batch の seed には載せない前提。
            if row.cursor_status == "active":
                rows.append(row)
        for row in self.fetch_cursors.values():
            if row.cursor_status == "active":
                rows.append(row)
        return rows

    def get_or_create_cursor(self, row: FetchCursorRow) -> FetchCursorRow:
        fingerprint = row.scope_fingerprint or cursor_scope_fingerprint(
            cursor_type=row.cursor_type,
            target_external_genre_id=row.target_external_genre_id,
            scope=dict(row.scope),
        )
        for existing in self.fetch_cursors.values():
            if existing.scope_fingerprint == fingerprint and existing.cursor_type == row.cursor_type:
                return existing

        cursor_id = row.cursor_id or f"fc_{uuid.uuid4().hex[:12]}"
        created = FetchCursorRow(
            cursor_type=row.cursor_type,
            cursor_id=cursor_id,
            target_external_genre_id=row.target_external_genre_id,
            scope=dict(row.scope),
            page=row.page,
            cursor_status=row.cursor_status,
            scope_fingerprint=fingerprint,
        )
        self.fetch_cursors[cursor_id] = created
        self.db_writer.write_rows(
            "fetch_cursor",
            (
                {
                    "fetch_cursor_id": cursor_id,
                    "source": SOURCE_RAKUTEN,
                    "source_api": SOURCE_API_ITEM_SEARCH,
                    "cursor_type": created.cursor_type,
                    "target_external_genre_id": created.target_external_genre_id,
                    "cursor_status": created.cursor_status,
                    "page": created.page,
                    "scope": created.scope,
                    "scope_fingerprint": fingerprint,
                },
            ),
        )
        return created

    def update_cursor_progress(
        self,
        *,
        cursor_id: str,
        page: int,
        cursor_status: str = "active",
    ) -> None:
        existing = self.fetch_cursors.get(cursor_id)
        if existing is None:
            return
        updated = FetchCursorRow(
            cursor_type=existing.cursor_type,
            cursor_id=existing.cursor_id,
            target_external_genre_id=existing.target_external_genre_id,
            scope=dict(existing.scope),
            page=page,
            cursor_status=cursor_status,
            scope_fingerprint=existing.scope_fingerprint,
        )
        self.fetch_cursors[cursor_id] = updated
        self.db_writer.write_rows(
            "fetch_cursor",
            (
                {
                    "fetch_cursor_id": cursor_id,
                    "page": page,
                    "cursor_status": cursor_status,
                },
            ),
        )

    def save_raw(self, artifact: RawItemSearchArtifact) -> bool:
        """Persist Raw. Returns False when identical content_hash is skipped."""

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
                "cursor_id": artifact.cursor_id,
                "cursor_type": artifact.cursor_type,
                "page": artifact.page,
                "source": SOURCE_RAKUTEN,
                "source_api": SOURCE_API_ITEM_SEARCH,
            }
            return False

        self.object_storage.put_object(
            ref,
            body=artifact.body,
            content_type="application/json",
        )
        self.raw_metadata[artifact.object_key] = {
            "object_key": artifact.object_key,
            "content_hash": artifact.content_hash,
            "api_call_log_id": artifact.api_call_log_id,
            "cursor_id": artifact.cursor_id,
            "cursor_type": artifact.cursor_type,
            "page": artifact.page,
            "source": SOURCE_RAKUTEN,
            "source_api": SOURCE_API_ITEM_SEARCH,
            "import_status": "raw_saved",
        }
        self.db_writer.write_rows(
            "raw_product_metadata",
            (dict(self.raw_metadata[artifact.object_key]),),
        )
        return True

    def record_api_call(
        self,
        *,
        api_call_log_id: str,
        fetch_cursor_id: str | None,
        cursor_type: str,
        status: str,
        page: int | None = None,
        error_code: str | None = None,
    ) -> None:
        params: dict[str, object] = {"cursor_type": cursor_type}
        if fetch_cursor_id is not None:
            params["fetch_cursor_id"] = fetch_cursor_id
        if page is not None:
            params["page"] = page
        emit_api_call(
            api_call_logs=self.api_call_logs,
            api_call_log_writer=self.api_call_log_writer,
            batch_run_id=self._batch_run_id,
            trace_id=self._trace_id,
            api_call_log_id=api_call_log_id,
            source_api="item_search",
            call_status=status,
            memory_entry={
                "api_call_log_id": api_call_log_id,
                "fetch_cursor_id": fetch_cursor_id,
                "cursor_type": cursor_type,
                "page": page,
                "status": status,
                "error_code": error_code,
            },
            request_params_json=params,
            error_code=error_code,
        )

    def record_error(self, *, code: str, summary: str, cursor_id: str | None = None) -> None:
        detail: dict[str, object] = {}
        if cursor_id is not None:
            detail["cursor_id"] = cursor_id
        emit_error(
            error_logs=self.error_logs,
            error_log_writer=self.error_log_writer,
            batch_run_id=self._batch_run_id,
            trace_id=self._trace_id,
            code=code,
            summary=summary,
            memory_extra={"cursor_id": cursor_id},
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
