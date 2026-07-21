"""In-memory repositories for BATCH-012 scaffold / UT.

- item / item_semantic READ ONLY
- BATCH-011 hash handoff READ ONLY（再算出しない）
- item_feature UPSERT（IF-DB-BATCH-013）。raw のみ。normalized 非更新（BATCH-013）
- Queue UPDATE only（INSERT 禁止 / item_semantic DML 禁止）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from batch.application.item_feature.adapter import (
    DEFAULT_NORMALIZATION_VERSION,
    MVP_FEATURE_CODES,
    ConceptFeatureRule,
)
from batch.application.item_feature.models import (
    ConceptRef,
    FeatureInputHashHandoff,
    ItemFeatureUpsertRow,
    ItemRow,
    ItemSemanticRow,
    QueueRow,
)
from batch.infrastructure.db import DbWriter

DEFAULT_SOURCE = "rakuten"


@dataclass(frozen=True)
class ExistingFeatureAxis:
    """skip 判定用の既存 item_feature 軸（読取のみ）。"""

    feature_code: str
    feature_input_hash: str
    feature_normalization_version_id: str
    has_raw_value: bool = True


@dataclass
class ItemFeatureRepositories:
    db_writer: DbWriter
    seed_queues: list[QueueRow] = field(default_factory=list)
    seed_items: list[ItemRow] = field(default_factory=list)
    seed_semantics: list[ItemSemanticRow] = field(default_factory=list)
    # item_id -> BATCH-011 handoff
    seed_handoffs: list[FeatureInputHashHandoff] = field(default_factory=list)
    # (item_id, semantic_config_version_id) -> existing axes
    seed_features: dict[tuple[str, str], list[ExistingFeatureAxis]] = field(default_factory=dict)
    concept_feature_rules: ConceptFeatureRule = field(default_factory=dict)
    current_normalization_version_id: str = DEFAULT_NORMALIZATION_VERSION

    queues: dict[str, dict[str, object]] = field(default_factory=dict)
    items: dict[str, dict[str, object]] = field(default_factory=dict)
    semantics: dict[str, dict[str, object]] = field(default_factory=dict)
    handoffs: dict[str, FeatureInputHashHandoff] = field(default_factory=dict)
    features: dict[tuple[str, str], list[ExistingFeatureAxis]] = field(default_factory=dict)

    item_feature_write_count: int = 0
    item_semantic_write_count: int = 0
    queue_insert_count: int = 0
    upsert_rows: list[ItemFeatureUpsertRow] = field(default_factory=list)
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
                    "item_name": item.item_name,
                    "genre_id": item.genre_id,
                    "genre_name": item.genre_name,
                },
            )
        for sem in self.seed_semantics:
            self.semantics.setdefault(
                sem.item_id,
                {
                    "item_id": sem.item_id,
                    "semantic_config_version_id": sem.semantic_config_version_id,
                    "semantic_json": dict(sem.semantic_json),
                },
            )
        for handoff in self.seed_handoffs:
            self.handoffs.setdefault(handoff.item_id, handoff)
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
            genre_id=str(row["genre_id"]) if row.get("genre_id") is not None else None,
            genre_name=str(row["genre_name"]) if row.get("genre_name") is not None else None,
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

    def load_hash_handoff(self, *, item_id: str) -> FeatureInputHashHandoff | None:
        """BATCH-011（IF-DB-BATCH-012）から引き渡された hash を読取（再算出しない）。"""

        return self.handoffs.get(item_id)

    @staticmethod
    def extract_concepts(semantic_json: dict[str, Any]) -> tuple[ConceptRef, ...]:
        concepts = semantic_json.get("concepts") or []
        refs: list[ConceptRef] = []
        if isinstance(concepts, list):
            for entry in concepts:
                if isinstance(entry, dict):
                    code = entry.get("concept_code")
                    if code is None or not str(code).strip():
                        continue
                    confidence = entry.get("confidence")
                    weight = entry.get("source_weight")
                    refs.append(
                        ConceptRef(
                            concept_code=str(code).strip(),
                            confidence=float(confidence) if confidence is not None else 1.0,
                            source_weight=float(weight) if weight is not None else 1.0,
                        )
                    )
                elif isinstance(entry, str) and entry.strip():
                    refs.append(ConceptRef(concept_code=entry.strip()))
        return tuple(refs)

    def should_skip_feature_generation(
        self,
        *,
        item_id: str,
        semantic_config_version_id: str,
        feature_input_hash: str,
        feature_normalization_version_id: str,
    ) -> bool:
        """§9.3: raw 8 軸すべてが同一 hash + normalization version で存在すれば skip.

        BATCH-011 §9.4 と異なり、normalized の有無は skip 判定に含めない。
        """

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
            if axis.feature_normalization_version_id != feature_normalization_version_id:
                return False
            if not axis.has_raw_value:
                return False
        return True

    def upsert_item_feature(self, rows: tuple[ItemFeatureUpsertRow, ...]) -> None:
        """IF-DB-BATCH-013: item_feature へ raw 8 軸を Upsert（normalized 非指定）."""

        if not rows:
            return
        payload = tuple(
            {
                "item_id": r.item_id,
                "semantic_config_version_id": r.semantic_config_version_id,
                "feature_code": r.feature_code,
                "feature_input_hash": r.feature_input_hash,
                "feature_normalization_version_id": r.feature_normalization_version_id,
                "raw_feature_value": r.raw_feature_value,
                "generated_at": r.generated_at,
                "op": "if_db_batch_013_upsert",
            }
            for r in rows
        )
        self.upsert_rows.extend(rows)
        self.item_feature_write_count += len(rows)
        self.db_writer.write_rows("item_feature", payload)

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
                        "op": "feature_success_keep_processing",
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
