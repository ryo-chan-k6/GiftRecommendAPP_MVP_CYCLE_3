"""BATCH-016 分布統計 Aggregator（MOD-BATCH-038 内包）.

仕様書 §9: sample_count / mean / stddev / min / max。
stddev は sample_count < 2 のとき NULL（None）。
MVP Social / Symbolic feature codes は Featureルール定義書の固定名に従う。
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from collections.abc import Sequence

from batch.application.distribution_metrics.models import (
    AggregationScope,
    DistributionStats,
    ItemFeatureRow,
    ItemMeaningRow,
    MetricUpsertRow,
    ScopeResolve,
    UserMeaningRow,
)

# MVP 8 軸（Featureルール定義書 固定名）
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

SOCIAL_FEATURE_CODES: tuple[str, ...] = (
    "formality",
    "safety",
    "brand_appropriateness",
)
SYMBOLIC_FEATURE_CODES: tuple[str, ...] = (
    "emotion",
    "novelty",
    "intimacy",
    "symbolic_identity",
    "story_richness",
)


def compute_distribution_stats(values: Sequence[float]) -> DistributionStats:
    """value list から共通統計列を算出する。"""

    n = len(values)
    if n == 0:
        return DistributionStats(
            sample_count=0,
            mean=0.0,
            stddev=None,
            min_value=None,
            max_value=None,
        )
    mean = float(statistics.fmean(values))
    stddev: float | None
    if n < 2:
        stddev = None
    else:
        stddev = float(statistics.stdev(values))
    return DistributionStats(
        sample_count=n,
        mean=mean,
        stddev=stddev,
        min_value=float(min(values)),
        max_value=float(max(values)),
    )


def _scope_fields(scope: ScopeResolve) -> tuple[AggregationScope, str | None]:
    return scope.aggregation_scope, scope.aggregation_key


def aggregate_feature_metrics(
    *,
    features: Sequence[ItemFeatureRow],
    scope: ScopeResolve,
    batch_run_id: str,
) -> list[MetricUpsertRow]:
    """item_feature → feature_distribution_metric（raw / normalized × feature_code）。"""

    agg_scope, agg_key = _scope_fields(scope)
    version = scope.semantic_config_version_id
    raw_by_code: dict[str, list[float]] = defaultdict(list)
    norm_by_code: dict[str, list[float]] = defaultdict(list)

    for row in features:
        if row.semantic_config_version_id != version:
            continue
        if row.feature_code not in MVP_FEATURE_CODES:
            continue
        if row.raw_feature_value is not None:
            raw_by_code[row.feature_code].append(float(row.raw_feature_value))
        if row.normalized_feature_value is not None:
            norm_by_code[row.feature_code].append(float(row.normalized_feature_value))

    rows: list[MetricUpsertRow] = []
    for code in MVP_FEATURE_CODES:
        for layer, buckets in (("raw", raw_by_code), ("normalized", norm_by_code)):
            values = buckets.get(code, [])
            if not values:
                continue
            stats = compute_distribution_stats(values)
            rows.append(
                MetricUpsertRow(
                    table="feature_distribution_metric",
                    batch_run_id=batch_run_id,
                    semantic_config_version_id=version,
                    aggregation_scope=agg_scope,
                    aggregation_key=agg_key,
                    value_layer=layer,
                    feature_code=code,
                    sample_count=stats.sample_count,
                    mean=stats.mean,
                    stddev=stats.stddev,
                    min_value=stats.min_value,
                    max_value=stats.max_value,
                )
            )
    return rows


def aggregate_meaning_metrics(
    *,
    item_meanings: Sequence[ItemMeaningRow],
    user_meanings: Sequence[UserMeaningRow],
    scope: ScopeResolve,
    batch_run_id: str,
    include_user_meaning: bool,
) -> list[MetricUpsertRow]:
    """item_meaning（必須）/ user_meaning（任意）→ meaning_distribution_metric。"""

    agg_scope, agg_key = _scope_fields(scope)
    version = scope.semantic_config_version_id
    rows: list[MetricUpsertRow] = []

    # item: social / symbolic。feature_normalization_version_id 混在時は行分割
    item_buckets: dict[tuple[str | None, str], list[float]] = defaultdict(list)
    for row in item_meanings:
        if row.semantic_config_version_id != version:
            continue
        norm_ver = row.feature_normalization_version_id
        item_buckets[(norm_ver, "social")].append(float(row.item_social))
        item_buckets[(norm_ver, "symbolic")].append(float(row.item_symbolic))

    for (norm_ver, layer), values in sorted(item_buckets.items(), key=lambda x: str(x[0])):
        stats = compute_distribution_stats(values)
        rows.append(
            MetricUpsertRow(
                table="meaning_distribution_metric",
                batch_run_id=batch_run_id,
                semantic_config_version_id=version,
                aggregation_scope=agg_scope,
                aggregation_key=agg_key,
                value_layer=layer,
                entity_type="item",
                feature_normalization_version_id=norm_ver,
                sample_count=stats.sample_count,
                mean=stats.mean,
                stddev=stats.stddev,
                min_value=stats.min_value,
                max_value=stats.max_value,
            )
        )

    if include_user_meaning:
        user_buckets: dict[tuple[str | None, str], list[float]] = defaultdict(list)
        for row in user_meanings:
            if row.semantic_config_version_id != version:
                continue
            norm_ver = row.feature_normalization_version_id
            user_buckets[(norm_ver, "social")].append(float(row.user_social))
            user_buckets[(norm_ver, "symbolic")].append(float(row.user_symbolic))
            if row.lambda_ctx is not None:
                user_buckets[(norm_ver, "lambda_ctx")].append(float(row.lambda_ctx))

        for (norm_ver, layer), values in sorted(user_buckets.items(), key=lambda x: str(x[0])):
            stats = compute_distribution_stats(values)
            rows.append(
                MetricUpsertRow(
                    table="meaning_distribution_metric",
                    batch_run_id=batch_run_id,
                    semantic_config_version_id=version,
                    aggregation_scope=agg_scope,
                    aggregation_key=agg_key,
                    value_layer=layer,
                    entity_type="user",
                    feature_normalization_version_id=norm_ver,
                    sample_count=stats.sample_count,
                    mean=stats.mean,
                    stddev=stats.stddev,
                    min_value=stats.min_value,
                    max_value=stats.max_value,
                )
            )

    return rows


def aggregate_normalization_metrics(
    *,
    features: Sequence[ItemFeatureRow],
    scope: ScopeResolve,
    batch_run_id: str,
) -> list[MetricUpsertRow]:
    """item_feature → normalization_distribution_metric（raw / sigmoid）。"""

    agg_scope, agg_key = _scope_fields(scope)
    version = scope.semantic_config_version_id
    # key: (feature_code, value_layer, feature_normalization_version_id)
    buckets: dict[tuple[str, str, str | None], list[float]] = defaultdict(list)

    for row in features:
        if row.semantic_config_version_id != version:
            continue
        if row.feature_code not in MVP_FEATURE_CODES:
            continue
        norm_ver = row.feature_normalization_version_id
        if row.raw_feature_value is not None:
            buckets[(row.feature_code, "raw", norm_ver)].append(float(row.raw_feature_value))
        if row.normalized_feature_value is not None:
            buckets[(row.feature_code, "sigmoid", norm_ver)].append(
                float(row.normalized_feature_value)
            )

    rows: list[MetricUpsertRow] = []
    for (code, layer, norm_ver), values in sorted(buckets.items(), key=lambda x: (x[0][0], x[0][1])):
        if not values:
            continue
        stats = compute_distribution_stats(values)
        sigma_zero: int | None = None
        if layer == "sigmoid":
            # n>=2 かつ分散 0（全値同一）のとき寄与件数 = sample_count、それ以外は 0
            if stats.sample_count >= 2 and stats.stddev == 0.0:
                sigma_zero = stats.sample_count
            else:
                sigma_zero = 0
        rows.append(
            MetricUpsertRow(
                table="normalization_distribution_metric",
                batch_run_id=batch_run_id,
                semantic_config_version_id=version,
                aggregation_scope=agg_scope,
                aggregation_key=agg_key,
                value_layer=layer,
                feature_code=code,
                feature_normalization_version_id=norm_ver,
                sample_count=stats.sample_count,
                mean=stats.mean,
                stddev=stats.stddev,
                min_value=stats.min_value,
                max_value=stats.max_value,
                sigma_zero_count=sigma_zero,
            )
        )
    return rows
