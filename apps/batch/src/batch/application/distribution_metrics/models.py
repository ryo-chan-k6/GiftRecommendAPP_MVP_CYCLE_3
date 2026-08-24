"""BATCH-016 分布メトリクス集計 domain models (in-memory / scaffold).

物理書込 IF = IF-DB-BATCH-016（3 Metric テーブル INSERT / UPSERT）。
隣接 IF（014 / 015 / VEC-001）は書込禁止。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

DistributionMetricsRunStatus = Literal["succeeded", "partially_succeeded", "failed"]
AggregationScope = Literal["batch_run", "daily", "semantic_config_version"]
TriggerMode = Literal["dispatch", "chain", "schedule"]
FeatureValueLayer = Literal["raw", "normalized"]
NormalizationValueLayer = Literal["raw", "sigmoid"]
MeaningValueLayer = Literal["social", "symbolic", "lambda_ctx"]
MeaningEntityType = Literal["item", "user"]
MetricTable = Literal[
    "feature_distribution_metric",
    "meaning_distribution_metric",
    "normalization_distribution_metric",
]


@dataclass(frozen=True)
class ItemFeatureRow:
    """item_feature 読取行（必須入力・書込禁止）。"""

    item_id: str
    semantic_config_version_id: str
    feature_code: str
    raw_feature_value: float | None = None
    normalized_feature_value: float | None = None
    feature_normalization_version_id: str | None = None
    feature_input_hash: str | None = None
    generated_at: datetime | None = None


@dataclass(frozen=True)
class ItemMeaningRow:
    """item_meaning 読取行（必須入力・書込禁止）。"""

    item_id: str
    semantic_config_version_id: str
    item_social: float
    item_symbolic: float
    feature_normalization_version_id: str | None = None


@dataclass(frozen=True)
class UserMeaningRow:
    """user_meaning 読取行（任意・フラグ OFF 既定）。"""

    user_id: str
    semantic_config_version_id: str
    user_social: float
    user_symbolic: float
    lambda_ctx: float | None = None
    feature_normalization_version_id: str | None = None


@dataclass(frozen=True)
class ItemEmbeddingRow:
    """item_embedding 読取行（任意監視・Upsert 禁止）。"""

    item_id: str
    model_version_id: str
    embedding_input_hash: str


@dataclass(frozen=True)
class ScopeResolve:
    """resolve_scope 結果（aggregation_scope / key / version）。"""

    aggregation_scope: AggregationScope
    aggregation_key: str | None
    semantic_config_version_id: str
    trigger_mode: TriggerMode


@dataclass(frozen=True)
class DistributionStats:
    """共通統計列（仕様書 §9.1）。stddev は sample_count < 2 で None。"""

    sample_count: int
    mean: float
    stddev: float | None
    min_value: float | None
    max_value: float | None


@dataclass(frozen=True)
class MetricUpsertRow:
    """IF-DB-BATCH-016 UPSERT 行（feature / meaning / normalization）。"""

    table: MetricTable
    batch_run_id: str
    semantic_config_version_id: str
    aggregation_scope: AggregationScope
    aggregation_key: str | None
    value_layer: str
    sample_count: int
    mean: float
    stddev: float | None
    min_value: float | None
    max_value: float | None
    feature_code: str | None = None
    entity_type: MeaningEntityType | None = None
    feature_normalization_version_id: str | None = None
    # normalization / sigmoid 層のみ。stddev==0.0 かつ n>=2 のとき寄与件数、それ以外は 0 または None
    sigma_zero_count: int | None = None


@dataclass
class DistributionMetricsJobResult:
    batch_id: str
    job_run_id: str
    status: DistributionMetricsRunStatus = "failed"
    completed_phases: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
    aggregation_scope: str | None = None
    aggregation_key: str | None = None
    semantic_config_version_id: str | None = None
    feature_metric_upsert_count: int = 0
    meaning_metric_upsert_count: int = 0
    normalization_metric_upsert_count: int = 0
    item_feature_write_count: int = 0
    item_meaning_write_count: int = 0
    item_embedding_write_count: int = 0
    embedding_hash_write_count: int = 0
    item_embedding_read_count: int = 0
    user_meaning_aggregated: bool = False
    include_item_embedding: bool = False
    include_user_meaning: bool = False
