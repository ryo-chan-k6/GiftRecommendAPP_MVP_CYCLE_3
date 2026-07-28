"""Repositories for BATCH-004 item recheck.

``list_seedable_items`` uses ``DbReader`` when injected (Wave A' seed SELECT).
Without a reader, in-memory ``seed_items`` remains for scaffold / UT.
Item / Staging / item.active_status は更新しない（004 境界）。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from batch.application.item_recheck.idempotency import (
    SOURCE_API_ITEM_SEARCH,
    SOURCE_RAKUTEN,
    cursor_scope_fingerprint,
)
from batch.application.item_recheck.models import (
    FetchCursorRow,
    ItemSeed,
    RawItemSearchArtifact,
    ResolvedCandidate,
)
from batch.infrastructure.db import DbReader, DbWriter
from batch.infrastructure.object_storage import ObjectRef, ObjectStorageClient

_SEED_COLUMNS = (
    "item_id",
    "source",
    "external_item_code",
    "active_status",
    "last_checked_at",
)


from batch.application.observability import (
    ApiCallLogWriter,
    ErrorLogWriter,
    PhaseLogWriter,
)
from batch.application.observability.binding import emit_api_call, emit_error, emit_phase

@dataclass
class ItemRecheckRepositories:
    """Facade that persists Raw / fetch_cursor / candidates / logs via infrastructure."""

    object_storage: ObjectStorageClient
    db_writer: DbWriter
    bucket: str
    db_reader: DbReader | None = None
    # 再確認対象の item seed（active + external_item_code）
    seed_items: list[ItemSeed] = field(default_factory=list)
    fetch_cursors: dict[str, FetchCursorRow] = field(default_factory=dict)
    raw_metadata: dict[str, dict[str, object]] = field(default_factory=dict)
    candidates: dict[tuple[str, str, str], dict[str, object]] = field(default_factory=dict)
    # 境界検証: Item / Staging を誤って作った / 更新した場合に検知する
    created_items: list[dict[str, object]] = field(default_factory=list)
    created_staging: list[dict[str, object]] = field(default_factory=list)
    updated_item_rows: list[dict[str, object]] = field(default_factory=list)
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

    def list_seedable_items(
        self,
        *,
        max_items: int,
        external_item_codes: tuple[str, ...] | None = None,
    ) -> list[ItemSeed]:
        """§9.2: active + external_item_code, older last_checked / lower popularity first.

        Explicit ``external_item_codes`` overrides priority (still capped by max_items).
        """

        if self.db_reader is not None:
            return self._list_seedable_items_from_db(
                max_items=max_items,
                external_item_codes=external_item_codes,
            )

        if external_item_codes:
            wanted = {code for code in external_item_codes if code}
            selected: list[ItemSeed] = []
            by_code = {
                item.external_item_code: item
                for item in self.seed_items
                if item.external_item_code
            }
            for code in external_item_codes:
                if code not in wanted:
                    continue
                if code in by_code:
                    selected.append(by_code[code])
                else:
                    # Explicit override may introduce codes not in seed (still recheckable)
                    selected.append(
                        ItemSeed(
                            source=SOURCE_RAKUTEN,
                            external_item_code=code,
                            active_status="active",
                        )
                    )
                if len(selected) >= max_items:
                    break
            return selected

        eligible = [
            item
            for item in self.seed_items
            if item.active_status == "active" and bool(item.external_item_code)
        ]
        eligible.sort(key=self._seed_sort_key)
        return eligible[: max(0, max_items)]

    def _list_seedable_items_from_db(
        self,
        *,
        max_items: int,
        external_item_codes: tuple[str, ...] | None,
    ) -> list[ItemSeed]:
        """SELECT via DbReader (equals-only; no popularity JOIN)."""

        reader = self.db_reader
        if reader is None:
            return []

        if external_item_codes:
            selected: list[ItemSeed] = []
            for code in external_item_codes:
                if not code:
                    continue
                result = reader.fetch_rows(
                    "item",
                    columns=_SEED_COLUMNS,
                    equals=(
                        ("source", SOURCE_RAKUTEN),
                        ("external_item_code", code),
                    ),
                    limit=1,
                )
                if result.rows:
                    selected.append(self._row_to_seed(result.rows[0]))
                else:
                    selected.append(
                        ItemSeed(
                            source=SOURCE_RAKUTEN,
                            external_item_code=code,
                            active_status="active",
                        )
                    )
                if len(selected) >= max_items:
                    break
            return selected

        fetch_limit = max(0, max_items)
        if fetch_limit == 0:
            return []

        # Fetch a bounded window then apply §9.2 sort in-process.
        # popularity lives on item_popularity_signal (JOIN out of DbReader scope).
        result = reader.fetch_rows(
            "item",
            columns=_SEED_COLUMNS,
            equals=(
                ("active_status", "active"),
                ("source", SOURCE_RAKUTEN),
            ),
            order_by=("last_checked_at",),
            limit=fetch_limit,
        )
        eligible = [
            seed
            for seed in (self._row_to_seed(row) for row in result.rows)
            if seed.active_status == "active" and bool(seed.external_item_code)
        ]
        eligible.sort(key=self._seed_sort_key)
        return eligible[:fetch_limit]

    @staticmethod
    def _seed_sort_key(item: ItemSeed) -> tuple[object, object, str]:
        # older last_checked first (None → oldest), lower popularity first (None last)
        checked = item.last_checked_at or datetime.min.replace(tzinfo=UTC)
        pop = item.popularity if item.popularity is not None else float("inf")
        return (checked, pop, item.external_item_code)

    def _row_to_seed(self, row: dict[str, object]) -> ItemSeed:
        last_checked = row.get("last_checked_at")
        checked_at: datetime | None
        if isinstance(last_checked, datetime):
            checked_at = last_checked if last_checked.tzinfo else last_checked.replace(tzinfo=UTC)
        else:
            checked_at = None
        item_id = row.get("item_id")
        return ItemSeed(
            source=str(row.get("source") or SOURCE_RAKUTEN),
            external_item_code=str(row.get("external_item_code") or ""),
            item_id=str(item_id) if item_id is not None else None,
            active_status=str(row.get("active_status") or "active"),
            last_checked_at=checked_at,
            popularity=None,
        )

    def get_or_create_recheck_cursor(self, *, external_item_code: str) -> FetchCursorRow:
        """get-or-create cursor_type=recheck, source_api=item_search, genre_id=NULL."""

        row = FetchCursorRow(
            cursor_type="recheck",
            target_external_genre_id=None,
            scope={"external_item_code": external_item_code},
            page=1,
            cursor_status="active",
        )
        return self.get_or_create_cursor(row)

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
            target_external_genre_id=None,
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
                    "target_external_genre_id": None,
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
        cursor_status: str = "exhausted",
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
        meta = {
            "object_key": artifact.object_key,
            "raw_metadata_id": f"rm_{uuid.uuid4().hex[:12]}",
            "content_hash": artifact.content_hash,
            "api_call_log_id": artifact.api_call_log_id,
            "cursor_id": artifact.cursor_id,
            "cursor_type": artifact.cursor_type,
            "page": artifact.page,
            "source": SOURCE_RAKUTEN,
            "source_api": SOURCE_API_ITEM_SEARCH,
            "import_status": "raw_saved",
        }
        self.raw_metadata[artifact.object_key] = meta
        self.db_writer.write_rows("raw_product_metadata", (dict(meta),))
        return True

    def upsert_candidate(self, candidate: ResolvedCandidate) -> dict[str, object]:
        """IF-DB-BATCH-020: upsert item_active_status_candidate (detected).

        Never writes candidate into raw_product_metadata. Never updates item.
        """

        key = (candidate.batch_run_id, candidate.source, candidate.external_item_code)
        existing = self.candidates.get(key)
        candidate_id = (
            str(existing["item_active_status_candidate_id"])
            if existing and existing.get("item_active_status_candidate_id")
            else f"casc_{uuid.uuid4().hex[:12]}"
        )
        now = candidate.detected_at or datetime.now(UTC)
        row: dict[str, object] = {
            "item_active_status_candidate_id": candidate_id,
            "batch_run_id": candidate.batch_run_id,
            "source": candidate.source,
            "external_item_code": candidate.external_item_code,
            "item_id": candidate.item_id,
            "candidate_active_status": candidate.candidate_active_status,
            "reason_code": candidate.reason_code,
            "detection_basis": candidate.detection_basis,
            "candidate_status": "detected",
            "detected_at": now,
            "applied_at": None,
            "raw_metadata_id": candidate.raw_metadata_id,
            "api_call_log_id": candidate.api_call_log_id,
        }
        self.candidates[key] = row
        # PK は DB default。冪等キー (batch_run_id, source, external_item_code) で UPSERT。
        persist_row = {
            "batch_run_id": candidate.batch_run_id,
            "source": candidate.source,
            "external_item_code": candidate.external_item_code,
            "item_id": candidate.item_id,
            "candidate_active_status": candidate.candidate_active_status,
            "reason_code": candidate.reason_code,
            "detection_basis": candidate.detection_basis,
            "candidate_status": "detected",
            "detected_at": now,
            "applied_at": None,
            "raw_metadata_id": candidate.raw_metadata_id,
            "api_call_log_id": candidate.api_call_log_id,
            "updated_at": now,
        }
        self.db_writer.upsert_rows(
            "item_active_status_candidate",
            (persist_row,),
            conflict_columns=("batch_run_id", "source", "external_item_code"),
            update_columns=(
                "item_id",
                "candidate_active_status",
                "reason_code",
                "detection_basis",
                "candidate_status",
                "detected_at",
                "applied_at",
                "raw_metadata_id",
                "api_call_log_id",
                "updated_at",
            ),
        )
        return row

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

    def record_error(self, *, code: str, summary: str, item_code: str | None = None) -> None:
        detail: dict[str, object] = {}
        if item_code is not None:
            detail["item_code"] = item_code
        emit_error(
            error_logs=self.error_logs,
            error_log_writer=self.error_log_writer,
            batch_run_id=self._batch_run_id,
            trace_id=self._trace_id,
            code=code,
            summary=summary,
            memory_extra={"item_code": item_code},
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
