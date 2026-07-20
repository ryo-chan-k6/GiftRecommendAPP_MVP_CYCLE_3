"""In-memory repositories for BATCH-015 scaffold / UT.

- item READ ONLY
- BATCH-014 handoff READ ONLY（IF-DB-BATCH-015 消費・再算出禁止）
- item_embedding UPSERT（IF-VEC-BATCH-001）
- Queue UPDATE only（INSERT 禁止）
- IF-DB-BATCH-016 分布メトリクス非書込
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from batch.application.item_embedding.models import (
    EmbeddingHashHandoff,
    ItemEmbeddingUpsertRow,
    ItemRow,
    QueueRow,
)
from batch.infrastructure.db import DbWriter

DEFAULT_SOURCE = "rakuten"
# MVP scaffold 既定の現行 Embedding model version（MOD-RECO-003 stub）
DEFAULT_EMBEDDING_MODEL_VERSION = "scaffold-embedding-model-v1"


@dataclass(frozen=True)
class ExistingEmbedding:
    """skip 判定用の既存 item_embedding 行.

    冪等キー: item_id + model_version_id + embedding_input_hash。
    """

    model_version_id: str
    embedding_input_hash: str
    has_vector: bool = True
    embedding_source_type: str = "item_text_context"


@dataclass
class ItemEmbeddingRepositories:
    """Facade: Queue / handoff / item_embedding Upsert / logs（MOD-BATCH-037）."""

    db_writer: DbWriter
    seed_queues: list[QueueRow] = field(default_factory=list)
    seed_items: list[ItemRow] = field(default_factory=list)
    seed_handoffs: list[EmbeddingHashHandoff] = field(default_factory=list)
    seed_embeddings: dict[str, list[ExistingEmbedding]] = field(default_factory=dict)

    queues: dict[str, dict[str, object]] = field(default_factory=dict)
    items: dict[str, dict[str, object]] = field(default_factory=dict)
    handoffs: dict[str, EmbeddingHashHandoff] = field(default_factory=dict)
    embeddings: dict[str, list[ExistingEmbedding]] = field(default_factory=dict)
    embedding_rows: dict[tuple[str, str, str], dict[str, object]] = field(default_factory=dict)

    item_embedding_write_count: int = 0
    item_write_count: int = 0
    queue_insert_count: int = 0
    hash_recompute_count: int = 0
    distribution_metric_write_count: int = 0
    upsert_rows: list[ItemEmbeddingUpsertRow] = field(default_factory=list)
    api_call_logs: list[dict[str, object]] = field(default_factory=list)
    error_logs: list[dict[str, object]] = field(default_factory=list)
    phase_logs: list[dict[str, object]] = field(default_factory=list)

    def __post_init__(self) -> None:
        for seed in self.seed_queues:
            self.queues.setdefault(
                seed.item_generation_queue_id,
                {
                    "item_generation_queue_id": seed.item_generation_queue_id,
                    "item_id": seed.item_id,
                    "generation_type": seed.generation_type,
                    "queue_status": seed.queue_status,
                    "retry_count": seed.retry_count,
                    "queued_at": seed.queued_at,
                    "started_at": seed.started_at,
                    "completed_at": seed.completed_at,
                    "error_message": seed.error_message,
                },
            )
        for item in self.seed_items:
            self.items.setdefault(
                item.item_id,
                {
                    "item_id": item.item_id,
                    "source": item.source,
                    "external_item_code": item.external_item_code,
                    "active_status": item.active_status,
                    "is_active": item.is_active,
                },
            )
        for handoff in self.seed_handoffs:
            # key: item_id（同一 item の最新 handoff を消費）
            self.handoffs[handoff.item_id] = handoff
        for key, rows in self.seed_embeddings.items():
            self.embeddings[key] = list(rows)
            for row in rows:
                if row.has_vector:
                    self.embedding_rows[
                        (key, row.model_version_id, row.embedding_input_hash)
                    ] = {
                        "item_id": key,
                        "model_version_id": row.model_version_id,
                        "embedding_input_hash": row.embedding_input_hash,
                        "embedding_source_type": row.embedding_source_type,
                        "has_vector": True,
                    }

    def list_target_queues(
        self,
        *,
        max_items: int,
        source: str = DEFAULT_SOURCE,
        queue_batch_size: int | None = None,
        item_ids: tuple[str, ...] | None = None,
        queue_ids: tuple[str, ...] | None = None,
    ) -> tuple[list[QueueRow], int]:
        """§9.1: embedding+queued/processing / semantic·feature+processing 継続."""

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

    def claim_or_continue(
        self,
        *,
        item_generation_queue_id: str,
        started_at: datetime | None = None,
    ) -> QueueRow | None:
        row = self.queues.get(item_generation_queue_id)
        if row is None:
            return None
        status = row.get("queue_status")
        gen = row.get("generation_type")
        ts = started_at or datetime.now(UTC)

        if gen == "embedding" and status == "queued":
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

        if status == "processing" and gen in {"embedding", "semantic", "feature"}:
            self.db_writer.write_rows(
                "item_generation_queue",
                (
                    {
                        "item_generation_queue_id": item_generation_queue_id,
                        "queue_status": "processing",
                        "op": "continue_processing",
                    },
                ),
            )
            return self._row_to_queue(row)

        return None

    def load_item(self, *, item_id: str) -> ItemRow:
        row = self.items.get(item_id)
        if row is None:
            raise KeyError(f"item not found: {item_id}")
        return ItemRow(
            item_id=str(row["item_id"]),
            source=str(row.get("source") or DEFAULT_SOURCE),
            external_item_code=str(row.get("external_item_code") or ""),
            active_status=str(row.get("active_status") or "active"),
            is_active=bool(row.get("is_active", True)),
        )

    def load_hash_handoff(self, *, item_id: str) -> EmbeddingHashHandoff | None:
        """IF-DB-BATCH-015 消費: BATCH-014 handoff を読取（再算出しない）."""

        return self.handoffs.get(item_id)

    def should_skip_embedding_generation(
        self,
        *,
        item_id: str,
        model_version_id: str,
        embedding_input_hash: str,
    ) -> bool:
        """§9.3: 同一 3 列キーの成功行あり → Embedding 生成 skip."""

        key = (item_id, model_version_id, embedding_input_hash)
        existing = self.embedding_rows.get(key)
        if existing is not None and existing.get("has_vector"):
            return True
        rows = self.embeddings.get(item_id, [])
        for row in rows:
            if row.model_version_id != model_version_id:
                continue
            if row.embedding_input_hash != embedding_input_hash:
                continue
            if not row.has_vector:
                continue
            return True
        return False

    def upsert_item_embedding(self, row: ItemEmbeddingUpsertRow) -> dict[str, object]:
        """IF-VEC-BATCH-001 Upsert（item_id + model_version_id + embedding_input_hash）."""

        key = (row.item_id, row.model_version_id, row.embedding_input_hash)
        existing = self.embedding_rows.get(key)
        item_embedding_id = (
            str(existing["item_embedding_id"])
            if existing is not None and existing.get("item_embedding_id")
            else f"ie_{uuid.uuid4().hex[:12]}"
        )
        # ベクトル全文は db_writer メタにも載せない（次元のみ）
        payload: dict[str, object] = {
            "item_embedding_id": item_embedding_id,
            "item_id": row.item_id,
            "model_version_id": row.model_version_id,
            "embedding_source_type": row.embedding_source_type,
            "embedding_input_hash": row.embedding_input_hash,
            "embedding_dimension": len(row.embedding_vector),
            "has_vector": True,
            "generated_at": row.generated_at,
            "op": "if_vec_batch_001_upsert",
        }
        # in-memory 保持用にベクトルは別キーで保持（ログ経路には出さない）
        payload["_embedding_vector"] = row.embedding_vector
        self.embedding_rows[key] = payload
        self.embeddings.setdefault(row.item_id, [])
        # refresh skip index
        self.embeddings[row.item_id] = [
            e
            for e in self.embeddings[row.item_id]
            if not (
                e.model_version_id == row.model_version_id
                and e.embedding_input_hash == row.embedding_input_hash
            )
        ]
        self.embeddings[row.item_id].append(
            ExistingEmbedding(
                model_version_id=row.model_version_id,
                embedding_input_hash=row.embedding_input_hash,
                has_vector=True,
                embedding_source_type=row.embedding_source_type,
            )
        )
        self.upsert_rows.append(row)
        self.item_embedding_write_count += 1
        # db_writer にはベクトル全文を渡さない
        log_payload = {k: v for k, v in payload.items() if k != "_embedding_vector"}
        self.db_writer.write_rows("item_embedding", (log_payload,))
        return payload

    def update_queue_status(
        self,
        *,
        item_generation_queue_id: str,
        queue_status: str,
        completed_at: datetime | None = None,
        error_message: str | None = None,
    ) -> None:
        """Queue 終端更新（succeeded / skipped / failed）。keep_processing なし."""

        row = self.queues.get(item_generation_queue_id)
        if row is None:
            raise KeyError(f"queue not found: {item_generation_queue_id}")
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

    def record_api_call(
        self,
        *,
        status: str,
        model: str,
        latency_ms: int | None,
        purpose: str = "item_embedding",
    ) -> None:
        """api_call_log メタのみ（secret / ベクトル全文禁止）."""

        self.api_call_logs.append(
            {
                "purpose": purpose,
                "status": status,
                "model": model,
                "latency_ms": latency_ms,
            }
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
