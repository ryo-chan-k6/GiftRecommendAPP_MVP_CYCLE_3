"""In-memory repositories for BATCH-011 scaffold / UT.

- item / item_semantic READ ONLY
- item_feature READ ONLY（skip 判定）。書込禁止（BATCH-012）
- Queue UPDATE only（INSERT 禁止）
- IF-DB-BATCH-012 handoff は in-memory 記録
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from batch.application.feature_input_hash.models import (
    HashHandoffRecord,
    ItemRow,
    ItemSemanticRow,
    QueueRow,
)
from batch.infrastructure.db import DbWriter

DEFAULT_SOURCE = "rakuten"
# MVP scaffold 既定の現行 normalization version（skip 判定キー）
DEFAULT_NORMALIZATION_VERSION = "scaffold-feature-norm-v1"


@dataclass(frozen=True)
class ExistingFeatureAxis:
    """skip 判定用の既存 item_feature 軸（読取のみ）。"""

    feature_code: str
    feature_input_hash: str
    feature_normalization_version_id: str
    has_normalized_value: bool = True


# MVP 8 軸（Feature定義書固定名と整合する scaffold コード）
MVP_FEATURE_CODES: tuple[str, ...] = (
    "formality",
    "safety",
    "brand_appropriateness",
    "emotion",
    "novelty",
    "intimacy",
    "symbolic_identity",
    "story_richness",
)


@dataclass
class FeatureInputHashRepositories:
    db_writer: DbWriter
    seed_queues: list[QueueRow] = field(default_factory=list)
    seed_items: list[ItemRow] = field(default_factory=list)
    seed_semantics: list[ItemSemanticRow] = field(default_factory=list)
    # (item_id, semantic_config_version_id) -> axes
    seed_features: dict[tuple[str, str], list[ExistingFeatureAxis]] = field(default_factory=dict)
    current_normalization_version_id: str = DEFAULT_NORMALIZATION_VERSION
    queues: dict[str, dict[str, object]] = field(default_factory=dict)
    items: dict[str, dict[str, object]] = field(default_factory=dict)
    semantics: dict[str, dict[str, object]] = field(default_factory=dict)
    features: dict[tuple[str, str], list[ExistingFeatureAxis]] = field(default_factory=dict)
    handoff_records: list[dict[str, object]] = field(default_factory=list)
    item_write_count: int = 0
    item_semantic_write_count: int = 0
    item_feature_write_count: int = 0
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
        for seed in self.seed_semantics:
            if seed.item_id not in self.semantics:
                self.semantics[seed.item_id] = {
                    "item_id": seed.item_id,
                    "semantic_config_version_id": seed.semantic_config_version_id,
                    "semantic_json": dict(seed.semantic_json),
                }
        for key, axes in self.seed_features.items():
            self.features[key] = list(axes)

    def list_target_queues(
        self,
        *,
        max_items: int,
        source: str = DEFAULT_SOURCE,
        queue_batch_size: int | None = None,
        item_ids: tuple[str, ...] | None = None,
        queue_ids: tuple[str, ...] | None = None,
    ) -> tuple[list[QueueRow], int]:
        """§9.1: semantic+processing 主経路 / feature+queued 副経路。embedding 除外."""

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

            if q.generation_type == "embedding":
                if q.queue_status in {"queued", "processing"}:
                    non_target += 1
                continue

            is_primary = q.generation_type == "semantic" and q.queue_status == "processing"
            is_secondary = q.generation_type == "feature" and q.queue_status == "queued"
            if not (is_primary or is_secondary):
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

        if gen == "semantic" and status == "processing":
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

        if gen == "feature" and status == "queued":
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

    def load_item_semantic(self, *, item_id: str) -> ItemSemanticRow:
        row = self.semantics.get(item_id)
        if row is None:
            raise KeyError(f"item_semantic not found: {item_id}")
        raw = row.get("semantic_json") or {}
        return ItemSemanticRow(
            item_id=str(row["item_id"]),
            semantic_config_version_id=str(row["semantic_config_version_id"]),
            semantic_json=dict(raw) if isinstance(raw, dict) else {},
        )

    def should_skip_feature_generation(
        self,
        *,
        item_id: str,
        semantic_config_version_id: str,
        feature_input_hash: str,
    ) -> bool:
        """§9.4 案A: 8 軸すべて同一 hash + 現行 normalization version + normalized あり."""

        axes = self.features.get((item_id, semantic_config_version_id), [])
        by_code = {a.feature_code: a for a in axes}
        if len(by_code) < len(MVP_FEATURE_CODES):
            return False
        for code in MVP_FEATURE_CODES:
            axis = by_code.get(code)
            if axis is None:
                return False
            if axis.feature_input_hash != feature_input_hash:
                return False
            if axis.feature_normalization_version_id != self.current_normalization_version_id:
                return False
            if not axis.has_normalized_value:
                return False
        return True

    def record_hash_handoff(self, record: HashHandoffRecord) -> None:
        """IF-DB-BATCH-012: in-memory handoff（item_feature 非書込）."""

        payload = {
            "item_id": record.item_id,
            "item_generation_queue_id": record.item_generation_queue_id,
            "semantic_config_version_id": record.semantic_config_version_id,
            "feature_input_hash": record.feature_input_hash,
            "feature_input_payload": dict(record.feature_input_payload),
            "op": "if_db_batch_012_handoff",
        }
        self.handoff_records.append(payload)
        self.db_writer.write_rows("feature_input_hash_handoff", (payload,))

    def update_queue_status(
        self,
        *,
        item_generation_queue_id: str,
        queue_status: str,
        completed_at: datetime | None = None,
        error_message: str | None = None,
        keep_processing: bool = False,
    ) -> None:
        row = self.queues.get(item_generation_queue_id)
        if row is None:
            raise KeyError(f"queue not found: {item_generation_queue_id}")
        if keep_processing:
            self.db_writer.write_rows(
                "item_generation_queue",
                (
                    {
                        "item_generation_queue_id": item_generation_queue_id,
                        "queue_status": "processing",
                        "op": "hash_success_keep_processing",
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
