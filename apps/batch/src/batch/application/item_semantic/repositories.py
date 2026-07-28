"""Repositories for BATCH-010 Item Semantic generation.

``list_claimable_queues`` / ``load_item`` / ``find_item_semantic`` use ``DbReader``
when injected (Wave D). Without a reader, in-memory seed remains for scaffold / UT.

genre / attributes / tags / reviews are not on ``item`` DDL → defaults when mapping
DB rows. ``semantic_input_hash`` is not on ``item_semantic`` DDL → None from DB /
in-memory only.

Write path (IF-DB-BATCH-011 / #1634 Wave 2):
- ``claim_queue`` → ``update_rows``（queued + semantic → processing）
- ``update_queue_status`` → ``update_rows``（終端）。成功時 keep_processing は DB no-op
- ``upsert_item_semantic`` → ``upsert_rows`` conflict ``(item_id, semantic_config_version_id)``
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from batch.application.item_semantic.models import (
    CLAIMABLE_GENERATION_TYPE,
    CLAIMABLE_QUEUE_STATUS,
    ItemContext,
    ItemSemanticRow,
    QueueRow,
)
from batch.infrastructure.db import DbReader, DbWriter

DEFAULT_SOURCE = "rakuten"


def _as_jsonb(value: dict[str, Any]) -> object:
    """Adapt dict for PostgreSQL jsonb placeholders (Scaffold では dict のまま可)."""

    try:
        from psycopg.types.json import Json
    except ImportError:  # pragma: no cover — CI/scaffold without psycopg
        return value
    return Json(value)

_QUEUE_COLUMNS = (
    "item_generation_queue_id",
    "item_id",
    "generation_type",
    "queue_status",
    "retry_count",
    "queued_at",
    "started_at",
    "completed_at",
    "error_message",
)
_ITEM_COLUMNS = (
    "item_id",
    "source",
    "external_item_code",
    "item_name",
    "item_caption",
    "active_status",
    "is_active",
)
_SEMANTIC_COLUMNS = (
    "item_semantic_id",
    "item_id",
    "semantic_config_version_id",
    "semantic_json",
    "generated_at",
)


from batch.application.observability import (
    ErrorLogWriter,
    PhaseLogWriter,
)
from batch.application.observability.binding import emit_error, emit_phase

@dataclass
class ItemSemanticRepositories:
    """Facade: Queue claim/update / Item read / item_semantic Upsert / logs."""

    db_writer: DbWriter
    db_reader: DbReader | None = None
    seed_queues: list[QueueRow] = field(default_factory=list)
    seed_items: list[ItemContext] = field(default_factory=list)
    seed_semantics: list[ItemSemanticRow] = field(default_factory=list)
    queues: dict[str, dict[str, object]] = field(default_factory=dict)
    items: dict[str, dict[str, object]] = field(default_factory=dict)
    item_semantics: dict[tuple[str, str], dict[str, object]] = field(default_factory=dict)
    written_item_semantic_rows: list[dict[str, object]] = field(default_factory=list)
    item_write_count: int = 0
    queue_insert_count: int = 0
    error_logs: list[dict[str, object]] = field(default_factory=list)
    phase_logs: list[dict[str, object]] = field(default_factory=list)
    phase_log_writer: PhaseLogWriter | None = None
    error_log_writer: ErrorLogWriter | None = None
    _batch_run_id: str | None = field(default=None, repr=False)
    _trace_id: str | None = field(default=None, repr=False)


    def bind_run(self, *, batch_run_id: str, trace_id: str | None = None) -> None:
        """Bind ``batch_run_id`` (= job_run_id UUID) for observability DB writes."""

        self._batch_run_id = batch_run_id
        self._trace_id = trace_id

    def __post_init__(self) -> None:
        for seed in self.seed_queues:
            if seed.item_generation_queue_id not in self.queues:
                self.queues[seed.item_generation_queue_id] = self._queue_to_dict(seed)
        for seed in self.seed_items:
            if seed.item_id not in self.items:
                self.items[seed.item_id] = self._item_to_dict(seed)
        for seed in self.seed_semantics:
            key = (seed.item_id, seed.semantic_config_version_id)
            if key not in self.item_semantics:
                self.item_semantics[key] = self._semantic_to_dict(seed)

    def list_claimable_queues(
        self,
        *,
        max_items: int,
        source: str = DEFAULT_SOURCE,
        queue_batch_size: int | None = None,
        item_ids: tuple[str, ...] | None = None,
        queue_ids: tuple[str, ...] | None = None,
    ) -> tuple[list[QueueRow], int]:
        """§9.1: generation_type=semantic かつ queued のみ。feature/embedding は skip 集計."""

        if self.db_reader is not None:
            return self._list_claimable_queues_from_db(
                max_items=max_items,
                source=source,
                queue_batch_size=queue_batch_size,
                item_ids=item_ids,
                queue_ids=queue_ids,
            )

        item_set = set(item_ids) if item_ids else None
        queue_set = set(queue_ids) if queue_ids else None
        limit = max_items if queue_batch_size is None else min(max_items, queue_batch_size)
        claimable: list[QueueRow] = []
        non_semantic_skip = 0

        rows = sorted(self.queues.values(), key=lambda r: str(r["item_generation_queue_id"]))
        for row in rows:
            q = self._row_to_queue(row)
            if queue_set is not None and q.item_generation_queue_id not in queue_set:
                continue
            if item_set is not None and q.item_id not in item_set:
                continue
            if q.generation_type != CLAIMABLE_GENERATION_TYPE:
                if q.queue_status == CLAIMABLE_QUEUE_STATUS:
                    non_semantic_skip += 1
                continue
            if q.queue_status != CLAIMABLE_QUEUE_STATUS:
                continue

            item = self.items.get(q.item_id)
            if item is not None and str(item.get("source") or DEFAULT_SOURCE) != source:
                continue

            claimable.append(q)
            if len(claimable) >= max(0, limit):
                break

        return claimable, non_semantic_skip

    def _list_claimable_queues_from_db(
        self,
        *,
        max_items: int,
        source: str,
        queue_batch_size: int | None,
        item_ids: tuple[str, ...] | None,
        queue_ids: tuple[str, ...] | None,
    ) -> tuple[list[QueueRow], int]:
        reader = self.db_reader
        if reader is None:
            return [], 0

        limit = max_items if queue_batch_size is None else min(max_items, queue_batch_size)
        candidate_rows: list[dict[str, object]] = []
        count_non_semantic = False

        if queue_ids:
            count_non_semantic = True
            for queue_id in queue_ids:
                if not queue_id:
                    continue
                result = reader.fetch_rows(
                    "item_generation_queue",
                    columns=_QUEUE_COLUMNS,
                    equals=(("item_generation_queue_id", queue_id),),
                    limit=1,
                )
                candidate_rows.extend(result.rows)
        elif item_ids:
            # per-item queued rows (all generation_type) so non-semantic skip is countable
            count_non_semantic = True
            for item_id in item_ids:
                if not item_id:
                    continue
                result = reader.fetch_rows(
                    "item_generation_queue",
                    columns=_QUEUE_COLUMNS,
                    equals=(
                        ("item_id", item_id),
                        ("queue_status", CLAIMABLE_QUEUE_STATUS),
                    ),
                    order_by=("item_generation_queue_id",),
                    limit=100,
                )
                candidate_rows.extend(result.rows)
        else:
            fetch_cap = max(0, limit)
            if fetch_cap == 0:
                return [], 0
            scan_target = max(fetch_cap, 1)
            fetch_limit = min(max(scan_target * 5, scan_target), 5000)
            result = reader.fetch_rows(
                "item_generation_queue",
                columns=_QUEUE_COLUMNS,
                equals=(
                    ("generation_type", CLAIMABLE_GENERATION_TYPE),
                    ("queue_status", CLAIMABLE_QUEUE_STATUS),
                ),
                order_by=("item_generation_queue_id",),
                limit=fetch_limit,
            )
            candidate_rows.extend(result.rows)

        claimable: list[QueueRow] = []
        non_semantic_skip = 0
        seen_ids: set[str] = set()

        for row in sorted(candidate_rows, key=lambda r: str(r["item_generation_queue_id"])):
            q = self._cache_queue_row(row)
            if q.item_generation_queue_id in seen_ids:
                continue
            seen_ids.add(q.item_generation_queue_id)

            if count_non_semantic and q.generation_type != CLAIMABLE_GENERATION_TYPE:
                if q.queue_status == CLAIMABLE_QUEUE_STATUS:
                    non_semantic_skip += 1
                continue
            if q.generation_type != CLAIMABLE_GENERATION_TYPE:
                continue
            if q.queue_status != CLAIMABLE_QUEUE_STATUS:
                continue

            item_row = self.items.get(q.item_id)
            if item_row is None:
                item_row = self._fetch_and_cache_item(q.item_id)
            if item_row is not None and str(item_row.get("source") or DEFAULT_SOURCE) != source:
                continue

            claimable.append(q)
            if len(claimable) >= max(0, limit):
                break

        return claimable, non_semantic_skip

    def claim_queue(
        self,
        *,
        item_generation_queue_id: str,
        started_at: datetime | None = None,
    ) -> QueueRow | None:
        """条件付き UPDATE: queued + semantic → processing."""

        row = self._ensure_queue_hydrated(item_generation_queue_id)
        if row is None:
            return None
        if row.get("queue_status") != "queued":
            return None
        if row.get("generation_type") != "semantic":
            return None

        ts = started_at or datetime.now(UTC)
        result = self.db_writer.update_rows(
            "item_generation_queue",
            set_values={"queue_status": "processing", "started_at": ts},
            equals=(
                ("item_generation_queue_id", item_generation_queue_id),
                ("queue_status", "queued"),
                ("generation_type", "semantic"),
            ),
        )
        if result.rows_affected == 0:
            # 競合（他 worker 先行 claim）
            return None

        row["queue_status"] = "processing"
        row["started_at"] = ts
        return self._row_to_queue(row)

    def load_item(self, *, item_id: str) -> ItemContext:
        row = self.items.get(item_id)
        if row is None and self.db_reader is not None:
            row = self._fetch_and_cache_item(item_id)
        if row is None:
            raise KeyError(f"item not found: {item_id}")
        return self._row_to_item(row)

    def find_item_semantic(
        self,
        *,
        item_id: str,
        semantic_config_version_id: str,
    ) -> ItemSemanticRow | None:
        key = (item_id, semantic_config_version_id)
        row = self.item_semantics.get(key)
        if row is None and self.db_reader is not None:
            result = self.db_reader.fetch_rows(
                "item_semantic",
                columns=_SEMANTIC_COLUMNS,
                equals=(
                    ("item_id", item_id),
                    ("semantic_config_version_id", semantic_config_version_id),
                ),
                limit=1,
            )
            if result.rows:
                return self._cache_semantic_row(result.rows[0])
            return None
        if row is None:
            return None
        return self._row_to_semantic(row)

    def upsert_item_semantic(
        self,
        *,
        item_id: str,
        semantic_config_version_id: str,
        semantic_json: dict[str, Any],
        semantic_input_hash: str | None,
        generated_at: datetime | None = None,
    ) -> ItemSemanticRow:
        """IF-DB-BATCH-011 Upsert."""

        ts = generated_at or datetime.now(UTC)
        key = (item_id, semantic_config_version_id)
        existing = self.item_semantics.get(key)
        item_semantic_id = (
            str(existing["item_semantic_id"])
            if existing is not None
            else str(uuid.uuid4())
        )
        # In-memory keeps semantic_input_hash for skip判定。DDL 列ではない。
        payload: dict[str, object] = {
            "item_semantic_id": item_semantic_id,
            "item_id": item_id,
            "semantic_config_version_id": semantic_config_version_id,
            "semantic_json": dict(semantic_json),
            "semantic_input_hash": semantic_input_hash,
            "generated_at": ts,
        }
        persist_row: dict[str, object] = {
            "item_semantic_id": item_semantic_id,
            "item_id": item_id,
            "semantic_config_version_id": semantic_config_version_id,
            "semantic_json": _as_jsonb(dict(semantic_json)),
            "generated_at": ts,
        }
        self.item_semantics[key] = payload
        self.written_item_semantic_rows.append(dict(payload))
        self.db_writer.upsert_rows(
            "item_semantic",
            (dict(persist_row),),
            conflict_columns=("item_id", "semantic_config_version_id"),
            update_columns=("semantic_json", "generated_at"),
        )
        return self._row_to_semantic(payload)

    def update_queue_status(
        self,
        *,
        item_generation_queue_id: str,
        queue_status: str,
        completed_at: datetime | None = None,
        error_message: str | None = None,
        keep_processing: bool = False,
    ) -> None:
        """Queue status 更新。semantic 成功時は processing 維持（DB no-op）。"""

        row = self._ensure_queue_hydrated(item_generation_queue_id)
        if row is None:
            raise KeyError(f"queue not found: {item_generation_queue_id}")

        if keep_processing:
            # 成功時: status は processing のまま。完了時刻は付けない（BATCH-015 まで）
            # claim 済みのため追加 UPDATE は不要（偽 op マーカー廃止）。
            return

        set_values: dict[str, object] = {"queue_status": queue_status}
        if completed_at is not None:
            set_values["completed_at"] = completed_at
            row["completed_at"] = completed_at
        if error_message is not None:
            set_values["error_message"] = error_message
            row["error_message"] = error_message
        row["queue_status"] = queue_status
        self.db_writer.update_rows(
            "item_generation_queue",
            set_values=set_values,
            equals=(("item_generation_queue_id", item_generation_queue_id),),
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

    def record_error(
        self,
        *,
        code: str,
        summary: str,
        item_generation_queue_id: str | None = None,
        item_id: str | None = None,
    ) -> None:
        detail: dict[str, object] = {}
        if item_generation_queue_id is not None:
            detail["item_generation_queue_id"] = item_generation_queue_id
        if item_id is not None:
            detail["item_id"] = item_id
        emit_error(
            error_logs=self.error_logs,
            error_log_writer=self.error_log_writer,
            batch_run_id=self._batch_run_id,
            trace_id=self._trace_id,
            code=code,
            summary=summary,
            memory_extra={"item_generation_queue_id": item_generation_queue_id, "item_id": item_id},
            detail=detail or None,
        )

    def _ensure_queue_hydrated(self, item_generation_queue_id: str) -> dict[str, object] | None:
        row = self.queues.get(item_generation_queue_id)
        if row is not None:
            return row
        if self.db_reader is None:
            return None
        result = self.db_reader.fetch_rows(
            "item_generation_queue",
            columns=_QUEUE_COLUMNS,
            equals=(("item_generation_queue_id", item_generation_queue_id),),
            limit=1,
        )
        if not result.rows:
            return None
        self._cache_queue_row(result.rows[0])
        return self.queues.get(item_generation_queue_id)

    def _fetch_and_cache_item(self, item_id: str) -> dict[str, object] | None:
        reader = self.db_reader
        if reader is None:
            return None
        result = reader.fetch_rows(
            "item",
            columns=_ITEM_COLUMNS,
            equals=(("item_id", item_id),),
            limit=1,
        )
        if not result.rows:
            return None
        return self._cache_item_row(result.rows[0])

    def _cache_queue_row(self, row: dict[str, object]) -> QueueRow:
        payload = dict(row)
        qid = str(payload["item_generation_queue_id"])
        self.queues[qid] = payload
        return self._row_to_queue(payload)

    def _cache_item_row(self, row: dict[str, object]) -> dict[str, object]:
        payload = {
            "item_id": str(row["item_id"]),
            "source": str(row.get("source") or DEFAULT_SOURCE),
            "external_item_code": str(row.get("external_item_code") or ""),
            "active_status": str(row.get("active_status") or "active"),
            "is_active": bool(row.get("is_active", True)),
            "item_name": row.get("item_name"),
            "item_caption": row.get("item_caption"),
            # DDL に無い列は既定（JOIN 解決は out of scope）
            "item_description": None,
            "genre_name": None,
            "attributes": [],
            "tags": [],
            "brand_name": None,
            "review_texts": [],
        }
        self.items[str(payload["item_id"])] = payload
        return payload

    def _cache_semantic_row(self, row: dict[str, object]) -> ItemSemanticRow:
        raw_json = row.get("semantic_json") or {}
        if not isinstance(raw_json, dict):
            raw_json = {}
        payload: dict[str, object] = {
            "item_semantic_id": str(row["item_semantic_id"]),
            "item_id": str(row["item_id"]),
            "semantic_config_version_id": str(row["semantic_config_version_id"]),
            "semantic_json": dict(raw_json),
            # DDL に semantic_input_hash は無い
            "semantic_input_hash": None,
        }
        key = (str(payload["item_id"]), str(payload["semantic_config_version_id"]))
        self.item_semantics[key] = payload
        return self._row_to_semantic(payload)

    @staticmethod
    def _queue_to_dict(seed: QueueRow) -> dict[str, object]:
        return {
            "item_generation_queue_id": seed.item_generation_queue_id,
            "item_id": seed.item_id,
            "generation_type": seed.generation_type,
            "queue_status": seed.queue_status,
            "retry_count": seed.retry_count,
            "queued_at": seed.queued_at,
            "started_at": seed.started_at,
            "completed_at": seed.completed_at,
            "error_message": seed.error_message,
        }

    @staticmethod
    def _item_to_dict(seed: ItemContext) -> dict[str, object]:
        return {
            "item_id": seed.item_id,
            "source": seed.source,
            "external_item_code": seed.external_item_code,
            "active_status": seed.active_status,
            "is_active": seed.is_active,
            "item_name": seed.item_name,
            "item_caption": seed.item_caption,
            "item_description": seed.item_description,
            "genre_name": seed.genre_name,
            "attributes": list(seed.attributes),
            "tags": list(seed.tags),
            "brand_name": seed.brand_name,
            "review_texts": list(seed.review_texts),
        }

    @staticmethod
    def _semantic_to_dict(seed: ItemSemanticRow) -> dict[str, object]:
        return {
            "item_semantic_id": seed.item_semantic_id,
            "item_id": seed.item_id,
            "semantic_config_version_id": seed.semantic_config_version_id,
            "semantic_json": dict(seed.semantic_json),
            "semantic_input_hash": seed.semantic_input_hash,
        }

    @staticmethod
    def _row_to_queue(row: dict[str, object]) -> QueueRow:
        return QueueRow(
            item_generation_queue_id=str(row["item_generation_queue_id"]),
            item_id=str(row["item_id"]),
            generation_type=row["generation_type"],  # type: ignore[arg-type]
            queue_status=row["queue_status"],  # type: ignore[arg-type]
            retry_count=int(row.get("retry_count") or 0),
            queued_at=row.get("queued_at"),  # type: ignore[arg-type]
            started_at=row.get("started_at"),  # type: ignore[arg-type]
            completed_at=row.get("completed_at"),  # type: ignore[arg-type]
            error_message=str(row["error_message"]) if row.get("error_message") else None,
        )

    @staticmethod
    def _row_to_item(row: dict[str, object]) -> ItemContext:
        attrs = row.get("attributes") or ()
        tags = row.get("tags") or ()
        reviews = row.get("review_texts") or ()
        return ItemContext(
            item_id=str(row["item_id"]),
            source=str(row.get("source") or DEFAULT_SOURCE),
            external_item_code=str(row.get("external_item_code") or ""),
            active_status=str(row.get("active_status") or "active"),
            is_active=bool(row.get("is_active", True)),
            item_name=str(row["item_name"]) if row.get("item_name") is not None else None,
            item_caption=str(row["item_caption"]) if row.get("item_caption") is not None else None,
            item_description=(
                str(row["item_description"]) if row.get("item_description") is not None else None
            ),
            genre_name=str(row["genre_name"]) if row.get("genre_name") is not None else None,
            attributes=tuple(str(a) for a in attrs),
            tags=tuple(str(t) for t in tags),
            brand_name=str(row["brand_name"]) if row.get("brand_name") is not None else None,
            review_texts=tuple(str(r) for r in reviews),
        )

    @staticmethod
    def _row_to_semantic(row: dict[str, object]) -> ItemSemanticRow:
        raw_json = row.get("semantic_json") or {}
        return ItemSemanticRow(
            item_semantic_id=str(row["item_semantic_id"]),
            item_id=str(row["item_id"]),
            semantic_config_version_id=str(row["semantic_config_version_id"]),
            semantic_json=dict(raw_json) if isinstance(raw_json, dict) else {},
            semantic_input_hash=(
                str(row["semantic_input_hash"]) if row.get("semantic_input_hash") else None
            ),
        )
