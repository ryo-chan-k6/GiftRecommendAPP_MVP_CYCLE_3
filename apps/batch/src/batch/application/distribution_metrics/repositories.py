"""Repositories for BATCH-016 分布メトリクス集計.

``load_item_features`` / ``load_item_meanings``（および任意の
``load_user_meanings`` / ``load_item_embeddings``）は ``DbReader`` 経由（Wave G）。

Metric UPSERT SQL 本格化は out of scope（scaffold / stub 書込のみ）。

- item_feature / item_meaning READ ONLY（必須入力）
- item_embedding / user_meaning READ ONLY（任意・フラグ OFF 既定）
- 3 Metric テーブル UPSERT（IF-DB-BATCH-016）のみ書込
- IF-DB-BATCH-014 / IF-DB-BATCH-015 / IF-VEC-BATCH-001 非書込
  （item_feature / item_meaning / item_embedding / embedding_hash write=0）
"""

from __future__ import annotations

from dataclasses import dataclass, field

from batch.application.distribution_metrics.models import (
    ItemEmbeddingRow,
    ItemFeatureRow,
    ItemMeaningRow,
    MetricUpsertRow,
    UserMeaningRow,
)
from batch.infrastructure.db import DbReader, DbWriter

_ITEM_FEATURE_COLUMNS = (
    "item_id",
    "semantic_config_version_id",
    "feature_code",
    "raw_feature_value",
    "normalized_feature_value",
    "feature_normalization_version_id",
)
_ITEM_MEANING_COLUMNS = (
    "item_id",
    "semantic_config_version_id",
    "item_social",
    "item_symbolic",
    "feature_normalization_version_id",
)
_ITEM_EMBEDDING_COLUMNS = (
    "item_id",
    "model_version_id",
    "embedding_input_hash",
)


def _feature_upsert_key(row: MetricUpsertRow) -> tuple[object, ...]:
    """feature_distribution_metric UNIQUE / 部分 UNIQUE キー.

    batch_run: (batch_run_id, semantic_config_version_id, feature_code, value_layer,
                aggregation_scope, aggregation_key)
    非 batch_run（部分 UNIQUE）: batch_run_id を除く
    """

    base = (
        row.semantic_config_version_id,
        row.feature_code,
        row.value_layer,
        row.aggregation_scope,
        row.aggregation_key,
    )
    if row.aggregation_scope == "batch_run":
        return (row.batch_run_id, *base)
    return base


def _meaning_upsert_key(row: MetricUpsertRow) -> tuple[object, ...]:
    """meaning_distribution_metric UNIQUE / 部分 UNIQUE キー."""

    base = (
        row.semantic_config_version_id,
        row.entity_type,
        row.value_layer,
        row.feature_normalization_version_id,
        row.aggregation_scope,
        row.aggregation_key,
    )
    if row.aggregation_scope == "batch_run":
        return (row.batch_run_id, *base)
    return base


def _normalization_upsert_key(row: MetricUpsertRow) -> tuple[object, ...]:
    """normalization_distribution_metric UNIQUE / 部分 UNIQUE キー."""

    base = (
        row.semantic_config_version_id,
        row.feature_code,
        row.value_layer,
        row.feature_normalization_version_id,
        row.aggregation_scope,
        row.aggregation_key,
    )
    if row.aggregation_scope == "batch_run":
        return (row.batch_run_id, *base)
    return base


def _upsert_rows(
    existing: list[MetricUpsertRow],
    incoming: tuple[MetricUpsertRow, ...],
    key_fn,
) -> int:
    """同一キーは上書き。戻り値は UPSERT 操作件数（incoming 件数）。"""

    index_by_key: dict[tuple[object, ...], int] = {
        key_fn(row): i for i, row in enumerate(existing)
    }
    for row in incoming:
        key = key_fn(row)
        if key in index_by_key:
            existing[index_by_key[key]] = row
        else:
            index_by_key[key] = len(existing)
            existing.append(row)
    return len(incoming)


def _optional_str(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: object | None) -> float | None:
    if value is None:
        return None
    return float(value)


@dataclass
class DistributionMetricsRepositories:
    """Facade: 入力読取 / IF-DB-BATCH-016 UPSERT / phase・error logs."""

    db_writer: DbWriter
    db_reader: DbReader | None = None
    seed_item_features: list[ItemFeatureRow] = field(default_factory=list)
    seed_item_meanings: list[ItemMeaningRow] = field(default_factory=list)
    seed_user_meanings: list[UserMeaningRow] = field(default_factory=list)
    seed_item_embeddings: list[ItemEmbeddingRow] = field(default_factory=list)

    item_features: list[ItemFeatureRow] = field(default_factory=list)
    item_meanings: list[ItemMeaningRow] = field(default_factory=list)
    user_meanings: list[UserMeaningRow] = field(default_factory=list)
    item_embeddings: list[ItemEmbeddingRow] = field(default_factory=list)

    feature_metric_rows: list[MetricUpsertRow] = field(default_factory=list)
    meaning_metric_rows: list[MetricUpsertRow] = field(default_factory=list)
    normalization_metric_rows: list[MetricUpsertRow] = field(default_factory=list)

    feature_metric_upsert_count: int = 0
    meaning_metric_upsert_count: int = 0
    normalization_metric_upsert_count: int = 0

    # 隣接 IF 非書込カウンタ（常に 0 を維持し UT で証明する）
    item_feature_write_count: int = 0
    item_meaning_write_count: int = 0
    item_embedding_write_count: int = 0
    embedding_hash_write_count: int = 0

    item_embedding_read_count: int = 0
    phase_logs: list[dict[str, object]] = field(default_factory=list)
    error_logs: list[dict[str, object]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.item_features = list(self.seed_item_features)
        self.item_meanings = list(self.seed_item_meanings)
        self.user_meanings = list(self.seed_user_meanings)
        self.item_embeddings = list(self.seed_item_embeddings)

    def load_item_features(self, *, semantic_config_version_id: str) -> tuple[ItemFeatureRow, ...]:
        if self.db_reader is not None:
            result = self.db_reader.fetch_rows(
                "item_feature",
                columns=_ITEM_FEATURE_COLUMNS,
                equals=(("semantic_config_version_id", semantic_config_version_id),),
                order_by=("item_id", "feature_code"),
            )
            return tuple(self._row_to_item_feature(row) for row in result.rows)
        return tuple(
            row
            for row in self.item_features
            if row.semantic_config_version_id == semantic_config_version_id
        )

    def load_item_meanings(self, *, semantic_config_version_id: str) -> tuple[ItemMeaningRow, ...]:
        if self.db_reader is not None:
            result = self.db_reader.fetch_rows(
                "item_meaning",
                columns=_ITEM_MEANING_COLUMNS,
                equals=(("semantic_config_version_id", semantic_config_version_id),),
                order_by=("item_id",),
            )
            return tuple(self._row_to_item_meaning(row) for row in result.rows)
        return tuple(
            row
            for row in self.item_meanings
            if row.semantic_config_version_id == semantic_config_version_id
        )

    def load_user_meanings(self, *, semantic_config_version_id: str) -> tuple[UserMeaningRow, ...]:
        # user_meaning に semantic_config_version_id 列は無い（recommendation_run JOIN が必要）。
        # DbReader JOIN 拡張 / E4 は out of scope。任意フラグ時も seed 経路のみ。
        return tuple(
            row
            for row in self.user_meanings
            if row.semantic_config_version_id == semantic_config_version_id
        )

    def load_item_embeddings(self) -> tuple[ItemEmbeddingRow, ...]:
        """任意監視入力の読取のみ。IF-VEC-BATCH-001 Upsert は行わない。"""

        if self.db_reader is not None:
            result = self.db_reader.fetch_rows(
                "item_embedding",
                columns=_ITEM_EMBEDDING_COLUMNS,
                order_by=("item_id", "model_version_id"),
            )
            rows = tuple(self._row_to_item_embedding(row) for row in result.rows)
            self.item_embedding_read_count = len(rows)
            return rows

        rows = tuple(self.item_embeddings)
        self.item_embedding_read_count = len(rows)
        return rows

    def persist_metrics(
        self,
        *,
        feature_rows: tuple[MetricUpsertRow, ...],
        meaning_rows: tuple[MetricUpsertRow, ...],
        normalization_rows: tuple[MetricUpsertRow, ...],
    ) -> None:
        """IF-DB-BATCH-016: 3 Metric テーブルへ UPSERT（同一 UNIQUE キーは上書き）。"""

        if feature_rows:
            ops = _upsert_rows(self.feature_metric_rows, feature_rows, _feature_upsert_key)
            self.feature_metric_upsert_count += ops
            self.db_writer.write_rows(
                "feature_distribution_metric",
                tuple(self._row_payload(r) for r in feature_rows),
            )
        if meaning_rows:
            ops = _upsert_rows(self.meaning_metric_rows, meaning_rows, _meaning_upsert_key)
            self.meaning_metric_upsert_count += ops
            self.db_writer.write_rows(
                "meaning_distribution_metric",
                tuple(self._row_payload(r) for r in meaning_rows),
            )
        if normalization_rows:
            ops = _upsert_rows(
                self.normalization_metric_rows, normalization_rows, _normalization_upsert_key
            )
            self.normalization_metric_upsert_count += ops
            self.db_writer.write_rows(
                "normalization_distribution_metric",
                tuple(self._row_payload(r) for r in normalization_rows),
            )

    def record_phase(self, *, phase: str, status: str) -> None:
        """物理 phase_log。Metric 完了は feature_distribution_metric_recorded のみ。"""

        self.phase_logs.append({"phase": phase, "status": status})

    def record_error(self, *, code: str, summary: str) -> None:
        self.error_logs.append({"code": code, "summary": summary})

    @staticmethod
    def _row_to_item_feature(row: dict[str, object]) -> ItemFeatureRow:
        return ItemFeatureRow(
            item_id=str(row["item_id"]),
            semantic_config_version_id=str(row["semantic_config_version_id"]),
            feature_code=str(row["feature_code"]),
            raw_feature_value=_optional_float(row.get("raw_feature_value")),
            normalized_feature_value=_optional_float(row.get("normalized_feature_value")),
            feature_normalization_version_id=_optional_str(
                row.get("feature_normalization_version_id")
            ),
        )

    @staticmethod
    def _row_to_item_meaning(row: dict[str, object]) -> ItemMeaningRow:
        return ItemMeaningRow(
            item_id=str(row["item_id"]),
            semantic_config_version_id=str(row["semantic_config_version_id"]),
            item_social=float(row["item_social"]),
            item_symbolic=float(row["item_symbolic"]),
            feature_normalization_version_id=_optional_str(
                row.get("feature_normalization_version_id")
            ),
        )

    @staticmethod
    def _row_to_item_embedding(row: dict[str, object]) -> ItemEmbeddingRow:
        return ItemEmbeddingRow(
            item_id=str(row["item_id"]),
            model_version_id=str(row["model_version_id"]),
            embedding_input_hash=str(row["embedding_input_hash"]),
        )

    @staticmethod
    def _row_payload(row: MetricUpsertRow) -> dict[str, object]:
        return {
            "table": row.table,
            "batch_run_id": row.batch_run_id,
            "semantic_config_version_id": row.semantic_config_version_id,
            "aggregation_scope": row.aggregation_scope,
            "aggregation_key": row.aggregation_key,
            "value_layer": row.value_layer,
            "feature_code": row.feature_code,
            "entity_type": row.entity_type,
            "feature_normalization_version_id": row.feature_normalization_version_id,
            "sample_count": row.sample_count,
            "mean": row.mean,
            "stddev": row.stddev,
            "min_value": row.min_value,
            "max_value": row.max_value,
            "sigma_zero_count": row.sigma_zero_count,
            "op": "if_db_batch_016_upsert",
        }
