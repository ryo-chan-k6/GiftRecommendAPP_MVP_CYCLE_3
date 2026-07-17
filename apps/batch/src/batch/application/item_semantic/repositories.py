"""In-memory repositories for BATCH-010 unit tests / scaffold wiring.

Production will replace these with real DB adapters while keeping:
- item / genre / attribute / tag READ ONLY
- item_semantic UPSERT only (IF-DB-BATCH-011)
- item_generation_queue UPDATE only (no INSERT — IF-DB-BATCH-010 is BATCH-009)
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
from batch.infrastructure.db import DbWriter

DEFAULT_SOURCE = "rakuten"


@dataclass
class ItemSemanticRepositories:
    """Facade: Queue claim/update / Item read / item_semantic Upsert / logs."""

    db_writer: DbWriter
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

    def claim_queue(
        self,
        *,
        item_generation_queue_id: str,
        started_at: datetime | None = None,
    ) -> QueueRow | None:
        """条件付き UPDATE: queued + semantic → processing."""

        row = self.queues.get(item_generation_queue_id)
        if row is None:
            return None
        if row.get("queue_status") != "queued":
            return None
        if row.get("generation_type") != "semantic":
            return None

        ts = started_at or datetime.now(UTC)
        row["queue_status"] = "processing"
        row["started_at"] = ts
        self.db_writer.write_rows(
            "item_generation_queue",
            (
                {
                    "item_generation_queue_id": item_generation_queue_id,
                    "queue_status": "processing",
                    "started_at": ts,
                    "op": "claim",
                },
            ),
        )
        return self._row_to_queue(row)

    def load_item(self, *, item_id: str) -> ItemContext:
        row = self.items.get(item_id)
        if row is None:
            raise KeyError(f"item not found: {item_id}")
        return self._row_to_item(row)

    def find_item_semantic(
        self,
        *,
        item_id: str,
        semantic_config_version_id: str,
    ) -> ItemSemanticRow | None:
        row = self.item_semantics.get((item_id, semantic_config_version_id))
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
            else f"is_{uuid.uuid4().hex[:12]}"
        )
        payload: dict[str, object] = {
            "item_semantic_id": item_semantic_id,
            "item_id": item_id,
            "semantic_config_version_id": semantic_config_version_id,
            "semantic_json": dict(semantic_json),
            "semantic_input_hash": semantic_input_hash,
            "generated_at": ts,
        }
        self.item_semantics[key] = payload
        self.written_item_semantic_rows.append(dict(payload))
        self.db_writer.write_rows("item_semantic", (dict(payload),))
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
        """Queue status 更新。semantic 成功時は processing 維持可。"""

        row = self.queues.get(item_generation_queue_id)
        if row is None:
            raise KeyError(f"queue not found: {item_generation_queue_id}")

        if keep_processing:
            # 成功時: status は processing のまま。完了時刻は付けない（BATCH-015 まで）
            self.db_writer.write_rows(
                "item_generation_queue",
                (
                    {
                        "item_generation_queue_id": item_generation_queue_id,
                        "queue_status": "processing",
                        "op": "semantic_success_keep_processing",
                    },
                ),
            )
            return

        row["queue_status"] = queue_status
        if completed_at is not None:
            row["completed_at"] = completed_at
        if error_message is not None:
            row["error_message"] = error_message
        self.db_writer.write_rows(
            "item_generation_queue",
            (
                {
                    "item_generation_queue_id": item_generation_queue_id,
                    "queue_status": queue_status,
                    "completed_at": completed_at,
                    "error_message": error_message,
                    "op": "update_status",
                },
            ),
        )

    def record_phase(self, *, phase: str, status: str) -> None:
        self.phase_logs.append({"phase": phase, "status": status})

    def record_error(
        self,
        *,
        code: str,
        summary: str,
        item_generation_queue_id: str | None = None,
        item_id: str | None = None,
    ) -> None:
        self.error_logs.append(
            {
                "code": code,
                "summary": summary,
                "item_generation_queue_id": item_generation_queue_id,
                "item_id": item_id,
            }
        )

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
