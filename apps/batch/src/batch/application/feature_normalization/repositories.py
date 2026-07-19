"""In-memory repositories for BATCH-013 scaffold / UT.

- item / item_feature raw READ ONLY（raw は BATCH-012 責務。変更しない）
- item_feature.normalized_feature_value UPDATE（IF-DB-BATCH-014）。raw 非更新
- item_meaning UPSERT（IF-DB-BATCH-014）。normalized 更新と同一トランザクション扱い
- Queue UPDATE only（INSERT 禁止 / item_semantic DML 禁止）
- normalization_distribution_metric 非書込（BATCH-016 責務）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from batch.application.feature_normalization.adapter import (
    DEFAULT_NORMALIZATION_VERSION,
    MVP_FEATURE_CODES,
)
from batch.application.feature_normalization.models import (
    ItemFeatureNormalizedUpdateRow,
    ItemMeaningUpsertRow,
    ItemRow,
    QueueRow,
    RawFeatureAxis,
)
from batch.infrastructure.db import DbWriter

DEFAULT_SOURCE = "rakuten"


@dataclass(frozen=True)
class ExistingNormalizedAxis:
    """skip 判定用の既存 normalized 軸（読取のみ）。"""

    feature_code: str
    feature_input_hash: str
    feature_normalization_version_id: str
    has_normalized_value: bool = True


@dataclass
class FeatureNormalizationRepositories:
    db_writer: DbWriter
    seed_queues: list[QueueRow] = field(default_factory=list)
    seed_items: list[ItemRow] = field(default_factory=list)
    # (item_id, semantic_config_version_id) -> raw 8 axes（BATCH-012 生成物）
    seed_raw_features: dict[tuple[str, str], list[RawFeatureAxis]] = field(default_factory=dict)
    # (item_id, semantic_config_version_id) -> existing normalized axes
    seed_normalized: dict[tuple[str, str], list[ExistingNormalizedAxis]] = field(
        default_factory=dict
    )
    # item_id -> semantic_config_version_id（Config Resolver の scaffold hint）
    seed_config_versions: dict[str, str] = field(default_factory=dict)
    current_normalization_version_id: str = DEFAULT_NORMALIZATION_VERSION

    queues: dict[str, dict[str, object]] = field(default_factory=dict)
    items: dict[str, dict[str, object]] = field(default_factory=dict)
    raw_features: dict[tuple[str, str], list[RawFeatureAxis]] = field(default_factory=dict)
    normalized: dict[tuple[str, str], list[ExistingNormalizedAxis]] = field(default_factory=dict)
    config_versions: dict[str, str] = field(default_factory=dict)

    item_feature_normalized_update_count: int = 0
    item_meaning_upsert_count: int = 0
    item_feature_raw_write_count: int = 0
    item_semantic_write_count: int = 0
    queue_insert_count: int = 0
    normalization_distribution_metric_write_count: int = 0
    normalized_update_rows: list[ItemFeatureNormalizedUpdateRow] = field(default_factory=list)
    item_meaning_rows: list[ItemMeaningUpsertRow] = field(default_factory=list)
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
        for key, axes in self.seed_raw_features.items():
            self.raw_features[key] = list(axes)
        for key, axes in self.seed_normalized.items():
            self.normalized[key] = list(axes)
        self.config_versions.update(self.seed_config_versions)

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
        )

    def resolve_semantic_config_version(self, *, item_id: str) -> str | None:
        """Config Resolver scaffold: item_id -> semantic_config_version_id。"""

        return self.config_versions.get(item_id)

    def load_raw_features(
        self,
        *,
        item_id: str,
        semantic_config_version_id: str,
    ) -> tuple[RawFeatureAxis, ...]:
        """BATCH-012（IF-DB-BATCH-013）が生成した raw 8 軸を読取（変更しない）。"""

        return tuple(self.raw_features.get((item_id, semantic_config_version_id), ()))

    def should_skip_normalization(
        self,
        *,
        item_id: str,
        semantic_config_version_id: str,
        feature_input_hash: str,
        feature_normalization_version_id: str,
    ) -> bool:
        """§9.3: normalized 8 軸すべてが同一 hash + 現行 version で存在すれば skip."""

        axes = self.normalized.get((item_id, semantic_config_version_id), [])
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
            if not axis.has_normalized_value:
                return False
        return True

    def persist_normalized_and_meaning(
        self,
        *,
        normalized_rows: tuple[ItemFeatureNormalizedUpdateRow, ...],
        item_meaning_row: ItemMeaningUpsertRow | None,
    ) -> None:
        """IF-DB-BATCH-014: normalized UPDATE + item_meaning UPSERT を同一トランザクションで実施。

        raw_feature_value は含めない（BATCH-012 責務）。
        item_meaning_row が None の場合は normalized 更新のみ（8 軸欠損等）。
        """

        if not normalized_rows:
            return
        payload = tuple(
            {
                "item_id": r.item_id,
                "semantic_config_version_id": r.semantic_config_version_id,
                "feature_code": r.feature_code,
                "feature_input_hash": r.feature_input_hash,
                "feature_normalization_version_id": r.feature_normalization_version_id,
                "normalized_feature_value": r.normalized_feature_value,
                "op": "if_db_batch_014_update_normalized",
            }
            for r in normalized_rows
        )
        self.normalized_update_rows.extend(normalized_rows)
        self.item_feature_normalized_update_count += len(normalized_rows)
        self.db_writer.write_rows("item_feature", payload)

        if item_meaning_row is not None:
            self.item_meaning_rows.append(item_meaning_row)
            self.item_meaning_upsert_count += 1
            self.db_writer.write_rows(
                "item_meaning",
                (
                    {
                        "item_id": item_meaning_row.item_id,
                        "semantic_config_version_id": item_meaning_row.semantic_config_version_id,
                        "item_social": item_meaning_row.item_social,
                        "item_symbolic": item_meaning_row.item_symbolic,
                        "generated_at": item_meaning_row.generated_at,
                        "op": "if_db_batch_014_upsert_meaning",
                    },
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
                        "op": "normalize_success_keep_processing",
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
