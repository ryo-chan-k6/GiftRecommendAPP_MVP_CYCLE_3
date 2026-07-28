"""Repositories for BATCH-014 Embedding入力hash算出.

``list_target_queues`` / ``load_item`` / skip 用 ``item_embedding`` SELECT は
``DbReader`` 経由（Wave E）。

queue フィルタ（embedding∈{queued,processing} OR semantic|feature+processing）は
equals 複数 fetch + in-process。genre/attrs/tags は DDL に無い → 空既定。

書込本配線（#1635 Wave 3 / #1690）:

- ``claim_or_continue``: embedding+queued → ``update_rows``（条件付き）。
  processing 継続（embedding/semantic/feature）は DB no-op
- ``update_queue_status``: keep_processing は DB no-op。終端は ``update_rows``
- ``record_hash_handoff``（IF-015）: 既存 ``upsert_rows`` 維持（E2 済・再実装しない）
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

from batch.application.embedding_input_hash.models import (
    EmbeddingHashHandoffRecord,
    ItemRow,
    QueueRow,
)
from batch.infrastructure.db import DbReader, DbWriter

DEFAULT_SOURCE = "rakuten"
# MVP scaffold 既定の現行 Embedding model version（skip 判定キー）
DEFAULT_EMBEDDING_MODEL_VERSION = "scaffold-embedding-model-v1"
# 入力構築ルール version（DB 物理列なし・batch 層概念。item_embedding §8.4）
DEFAULT_EMBEDDING_SOURCE_VERSION = "scaffold-embedding-source-v1"

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
    "catchcopy",
    "active_status",
    "is_active",
    "price",
)
_EMBEDDING_COLUMNS = (
    "item_id",
    "model_version_id",
    "embedding_input_hash",
    "embedding_vector",
)


@dataclass(frozen=True)
class ExistingEmbedding:
    """skip 判定用の既存 item_embedding 行（読取のみ）。

    冪等キー: item_id + model_version_id + embedding_input_hash（item_embedding §7）。
    """

    model_version_id: str
    embedding_input_hash: str
    has_vector: bool = True


@dataclass
class EmbeddingInputHashRepositories:
    db_writer: DbWriter
    db_reader: DbReader | None = None
    seed_queues: list[QueueRow] = field(default_factory=list)
    seed_items: list[ItemRow] = field(default_factory=list)
    # item_id -> 既存 Embedding 行（skip 判定）
    seed_embeddings: dict[str, list[ExistingEmbedding]] = field(default_factory=dict)
    queues: dict[str, dict[str, object]] = field(default_factory=dict)
    items: dict[str, dict[str, object]] = field(default_factory=dict)
    embeddings: dict[str, list[ExistingEmbedding]] = field(default_factory=dict)
    handoff_records: list[dict[str, object]] = field(default_factory=list)
    item_write_count: int = 0
    item_embedding_write_count: int = 0
    queue_insert_count: int = 0
    error_logs: list[dict[str, object]] = field(default_factory=list)
    phase_logs: list[dict[str, object]] = field(default_factory=list)

    def __post_init__(self) -> None:
        for seed in self.seed_queues:
            if seed.item_generation_queue_id not in self.queues:
                self.queues[seed.item_generation_queue_id] = {
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
        for seed in self.seed_items:
            if seed.item_id not in self.items:
                self.items[seed.item_id] = {
                    "item_id": seed.item_id,
                    "source": seed.source,
                    "external_item_code": seed.external_item_code,
                    "active_status": seed.active_status,
                    "is_active": seed.is_active,
                    "item_name": seed.item_name,
                    "catchcopy": seed.catchcopy,
                    "item_caption": seed.item_caption,
                    "genre_id": seed.genre_id,
                    "genre_name": seed.genre_name,
                    "attributes": list(seed.attributes),
                    "tags": list(seed.tags),
                    "price": seed.price,
                    "review_average": seed.review_average,
                    "review_count": seed.review_count,
                }
        for key, rows in self.seed_embeddings.items():
            self.embeddings[key] = list(rows)

    def list_target_queues(
        self,
        *,
        max_items: int,
        source: str = DEFAULT_SOURCE,
        queue_batch_size: int | None = None,
        item_ids: tuple[str, ...] | None = None,
        queue_ids: tuple[str, ...] | None = None,
    ) -> tuple[list[QueueRow], int]:
        """§9.1: embedding+queued/processing 対象 / semantic·feature+processing 継続。"""

        if self.db_reader is not None:
            return self._list_target_queues_from_db(
                max_items=max_items,
                source=source,
                queue_batch_size=queue_batch_size,
                item_ids=item_ids,
                queue_ids=queue_ids,
            )

        item_set = set(item_ids) if item_ids else None
        queue_set = set(queue_ids) if queue_ids else None
        limit = max_items if queue_batch_size is None else min(max_items, queue_batch_size)
        targets: list[QueueRow] = []
        non_target = 0

        rows = sorted(self.queues.values(), key=lambda r: str(r["item_generation_queue_id"]))
        for row in rows:
            q = self._row_to_queue(row)
            if queue_set is not None and q.item_generation_queue_id not in queue_set:
                continue
            if item_set is not None and q.item_id not in item_set:
                continue

            item = self.items.get(q.item_id)
            if item is not None and str(item.get("source") or DEFAULT_SOURCE) != source:
                continue

            is_embedding = q.generation_type == "embedding" and q.queue_status in {
                "queued",
                "processing",
            }
            is_continuation = (
                q.generation_type in {"semantic", "feature"} and q.queue_status == "processing"
            )
            if not (is_embedding or is_continuation):
                continue

            targets.append(q)
            if len(targets) >= max(0, limit):
                break

        return targets, non_target

    def _list_target_queues_from_db(
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

        if queue_ids:
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
            for item_id in item_ids:
                if not item_id:
                    continue
                result = reader.fetch_rows(
                    "item_generation_queue",
                    columns=_QUEUE_COLUMNS,
                    equals=(("item_id", item_id),),
                    order_by=("item_generation_queue_id",),
                    limit=100,
                )
                candidate_rows.extend(result.rows)
        else:
            fetch_cap = max(0, limit)
            if fetch_cap == 0:
                return [], 0
            fetch_limit = min(max(fetch_cap * 5, fetch_cap), 5000)
            # OR 条件は equals 複数 fetch + in-process（DbReader OR 拡張なし）
            filter_specs: tuple[tuple[tuple[str, object], ...], ...] = (
                (("generation_type", "embedding"), ("queue_status", "queued")),
                (("generation_type", "embedding"), ("queue_status", "processing")),
                (("generation_type", "semantic"), ("queue_status", "processing")),
                (("generation_type", "feature"), ("queue_status", "processing")),
            )
            for equals in filter_specs:
                result = reader.fetch_rows(
                    "item_generation_queue",
                    columns=_QUEUE_COLUMNS,
                    equals=equals,
                    order_by=("item_generation_queue_id",),
                    limit=fetch_limit,
                )
                candidate_rows.extend(result.rows)

        targets: list[QueueRow] = []
        non_target = 0
        seen_ids: set[str] = set()

        for row in sorted(candidate_rows, key=lambda r: str(r["item_generation_queue_id"])):
            q = self._cache_queue_row(row)
            if q.item_generation_queue_id in seen_ids:
                continue
            seen_ids.add(q.item_generation_queue_id)

            is_embedding = q.generation_type == "embedding" and q.queue_status in {
                "queued",
                "processing",
            }
            is_continuation = (
                q.generation_type in {"semantic", "feature"} and q.queue_status == "processing"
            )
            if not (is_embedding or is_continuation):
                continue

            item_row = self.items.get(q.item_id)
            if item_row is None:
                item_row = self._fetch_and_cache_item(q.item_id)
            if item_row is not None and str(item_row.get("source") or DEFAULT_SOURCE) != source:
                continue

            targets.append(q)
            if len(targets) >= max(0, limit):
                break

        return targets, non_target

    def claim_or_continue(
        self,
        *,
        item_generation_queue_id: str,
        started_at: datetime | None = None,
    ) -> QueueRow | None:
        """embedding claim（条件付き UPDATE）/ processing 継続（DB no-op）。"""

        row = self._ensure_queue_hydrated(item_generation_queue_id)
        if row is None:
            return None
        status = row.get("queue_status")
        gen = row.get("generation_type")
        ts = started_at or datetime.now(UTC)

        if gen == "embedding" and status == "queued":
            result = self.db_writer.update_rows(
                "item_generation_queue",
                set_values={"queue_status": "processing", "started_at": ts},
                equals=(
                    ("item_generation_queue_id", item_generation_queue_id),
                    ("queue_status", "queued"),
                    ("generation_type", "embedding"),
                ),
            )
            if result.rows_affected == 0:
                return None
            row["queue_status"] = "processing"
            row["started_at"] = ts
            return self._row_to_queue(row)

        if status == "processing" and gen in {"embedding", "semantic", "feature"}:
            # 既に processing。追加 UPDATE 不要（偽 op=continue_processing 廃止）。
            return self._row_to_queue(row)

        return None

    def load_item(self, *, item_id: str) -> ItemRow:
        row = self.items.get(item_id)
        if row is None and self.db_reader is not None:
            row = self._fetch_and_cache_item(item_id)
        if row is None:
            raise KeyError(f"item not found: {item_id}")
        return ItemRow(
            item_id=str(row["item_id"]),
            source=str(row.get("source") or DEFAULT_SOURCE),
            external_item_code=str(row.get("external_item_code") or ""),
            active_status=str(row.get("active_status") or "active"),
            is_active=bool(row.get("is_active", True)),
            item_name=str(row["item_name"]) if row.get("item_name") is not None else None,
            catchcopy=str(row["catchcopy"]) if row.get("catchcopy") is not None else None,
            item_caption=str(row["item_caption"]) if row.get("item_caption") is not None else None,
            genre_id=str(row["genre_id"]) if row.get("genre_id") is not None else None,
            genre_name=str(row["genre_name"]) if row.get("genre_name") is not None else None,
            attributes=tuple(str(a) for a in (row.get("attributes") or ())),
            tags=tuple(str(t) for t in (row.get("tags") or ())),
            price=int(row["price"]) if row.get("price") is not None else None,
            review_average=(
                float(row["review_average"]) if row.get("review_average") is not None else None
            ),
            review_count=int(row["review_count"]) if row.get("review_count") is not None else None,
        )

    def should_skip_embedding_generation(
        self,
        *,
        item_id: str,
        model_version_id: str,
        embedding_input_hash: str,
    ) -> bool:
        """§9.4: 同一 item_id + model_version_id + embedding_input_hash の Embedding が生成済み."""

        rows = self.embeddings.get(item_id)
        if rows is None and self.db_reader is not None:
            rows = self._fetch_and_cache_embeddings(item_id)
        if not rows:
            return False
        for row in rows:
            if row.model_version_id != model_version_id:
                continue
            if row.embedding_input_hash != embedding_input_hash:
                continue
            if not row.has_vector:
                continue
            return True
        return False

    def record_hash_handoff(self, record: EmbeddingHashHandoffRecord) -> None:
        """IF-DB-BATCH-015: item_embedding 非書込。中間表 item_embedding_input へ UPSERT."""

        now = datetime.now(UTC)
        context = dict(record.item_text_context)
        payload = {
            "item_id": record.item_id,
            "item_generation_queue_id": record.item_generation_queue_id,
            "model_version_id": record.model_version_id,
            "embedding_source_type": record.embedding_source_type,
            "embedding_source_version": record.embedding_source_version,
            "embedding_input_hash": record.embedding_input_hash,
            "item_text_context": context,
            "op": "if_db_batch_015_handoff",
        }
        self.handoff_records.append(payload)
        # DDL の item_text_context は text。canonical JSON 全文を保存（T2 Human 推奨）。
        context_text = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        persist_row = {
            "item_id": record.item_id,
            "model_version_id": record.model_version_id,
            "embedding_source_type": record.embedding_source_type,
            "embedding_input_hash": record.embedding_input_hash,
            "item_text_context": context_text,
            "item_generation_queue_id": record.item_generation_queue_id,
            "computed_at": now,
            "updated_at": now,
        }
        self.db_writer.upsert_rows(
            "item_embedding_input",
            (persist_row,),
            conflict_columns=("item_id", "model_version_id", "embedding_input_hash"),
            update_columns=(
                "embedding_source_type",
                "item_text_context",
                "item_generation_queue_id",
                "computed_at",
                "updated_at",
            ),
        )

    def update_queue_status(
        self,
        *,
        item_generation_queue_id: str,
        queue_status: str,
        completed_at: datetime | None = None,
        error_message: str | None = None,
        keep_processing: bool = False,
    ) -> None:
        """Queue status 更新。hash 成功時は processing 維持（DB no-op）。"""

        row = self._ensure_queue_hydrated(item_generation_queue_id)
        if row is None:
            raise KeyError(f"queue not found: {item_generation_queue_id}")
        if keep_processing:
            # 成功時: status は processing のまま。完了時刻は付けない（BATCH-015 継続）。
            # 偽 op=hash_success_keep_processing 廃止。
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

    def _fetch_and_cache_embeddings(self, item_id: str) -> list[ExistingEmbedding]:
        reader = self.db_reader
        if reader is None:
            return []
        result = reader.fetch_rows(
            "item_embedding",
            columns=_EMBEDDING_COLUMNS,
            equals=(("item_id", item_id),),
            order_by=("model_version_id",),
            limit=50,
        )
        rows = [
            ExistingEmbedding(
                model_version_id=str(row.get("model_version_id") or ""),
                embedding_input_hash=str(row.get("embedding_input_hash") or ""),
                has_vector=row.get("embedding_vector") is not None,
            )
            for row in result.rows
        ]
        self.embeddings[item_id] = rows
        return rows

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
            "catchcopy": row.get("catchcopy"),
            "item_caption": row.get("item_caption"),
            "price": row.get("price"),
            # DDL に無い列は既定（JOIN 解決は out of scope）
            "genre_id": None,
            "genre_name": None,
            "attributes": [],
            "tags": [],
            "review_average": None,
            "review_count": None,
        }
        self.items[str(payload["item_id"])] = payload
        return payload

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
