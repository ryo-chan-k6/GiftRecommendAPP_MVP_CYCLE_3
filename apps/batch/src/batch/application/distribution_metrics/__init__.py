"""BATCH-016 分布メトリクス集計 application package.

MOD-BATCH-038（Normalization Statistics Manager）内包。
Aggregator 論理名は docs 上維持し、追加採番しない。
"""

from batch.application.distribution_metrics.aggregator import (
    MVP_FEATURE_CODES,
    SOCIAL_FEATURE_CODES,
    SYMBOLIC_FEATURE_CODES,
    FeatureMetricAggregationError,
    aggregate_feature_metrics,
    aggregate_meaning_metrics,
    aggregate_normalization_metrics,
    compute_distribution_stats,
)
from batch.application.distribution_metrics.job import (
    BATCH_ID,
    DEFAULT_SEMANTIC_CONFIG_VERSION,
    DISTRIBUTION_METRICS_PHASES,
    PHASE_FEATURE_DISTRIBUTION_RECORDED,
    DistributionMetricsError,
    DistributionMetricsJob,
    resolve_scope,
)
from batch.application.distribution_metrics.models import (
    DistributionMetricsJobResult,
    DistributionStats,
    ItemEmbeddingRow,
    ItemFeatureRow,
    ItemMeaningRow,
    MetricUpsertRow,
    ScopeResolve,
    UserMeaningRow,
)
from batch.application.distribution_metrics.repositories import (
    DistributionMetricsRepositories,
    select_current_generation_item_feature_rows,
)

__all__ = [
    "BATCH_ID",
    "DEFAULT_SEMANTIC_CONFIG_VERSION",
    "DISTRIBUTION_METRICS_PHASES",
    "MVP_FEATURE_CODES",
    "PHASE_FEATURE_DISTRIBUTION_RECORDED",
    "SOCIAL_FEATURE_CODES",
    "SYMBOLIC_FEATURE_CODES",
    "DistributionMetricsError",
    "DistributionMetricsJob",
    "DistributionMetricsJobResult",
    "DistributionMetricsRepositories",
    "DistributionStats",
    "FeatureMetricAggregationError",
    "ItemEmbeddingRow",
    "ItemFeatureRow",
    "ItemMeaningRow",
    "MetricUpsertRow",
    "ScopeResolve",
    "UserMeaningRow",
    "aggregate_feature_metrics",
    "aggregate_meaning_metrics",
    "aggregate_normalization_metrics",
    "compute_distribution_stats",
    "resolve_scope",
    "select_current_generation_item_feature_rows",
]
