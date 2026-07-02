"""Social / Symbolic Match 集約ロジック（MOD-RECO-015 §8.3）。"""

from __future__ import annotations

from datetime import UTC, datetime

from reco.application.config_version_resolver.constants import (
    SOCIAL_FEATURE_WEIGHT_KEYS,
    SYMBOLIC_FEATURE_WEIGHT_KEYS,
)
from reco.application.feature_matcher.models import (
    FeatureMatchEntry,
    FeatureMatchResult,
)
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES

from .constants import (
    AGGREGATION_METHOD_WEIGHTED_AVERAGE,
    GUARD_CLIP_MAX,
    GUARD_CLIP_MIN,
    MATCH_VALUE_DECIMAL_PLACES,
    SOCIAL_FEATURE_WEIGHT_PREFIX,
    SYMBOLIC_FEATURE_WEIGHT_PREFIX,
)
from .errors import MeaningMatchAggregatorError
from .models import MeaningMatchAggregatorRunMetrics, MeaningMatchEntry, MeaningMatchResult


def run_meaning_match_aggregation(
    *,
    feature_match_result: FeatureMatchResult,
    config_versions: dict[str, str],
    default_matching_config_id: str,
) -> tuple[MeaningMatchResult, MeaningMatchAggregatorRunMetrics]:
    """feature_match_result から social_match / symbolic_match を集約する。"""
    if not feature_match_result.entries:
        empty = MeaningMatchResult(entries=(), total_aggregated=0)
        metrics = MeaningMatchAggregatorRunMetrics(
            meaning_match_aggregator_candidate_count=0,
            meaning_match_aggregator_latency_ms=0,
            meaning_match_value_out_of_range_count=0,
        )
        return empty, metrics

    social_weights = _resolve_feature_weights(
        config_versions,
        prefix=SOCIAL_FEATURE_WEIGHT_PREFIX,
        feature_keys=SOCIAL_FEATURE_WEIGHT_KEYS,
    )
    symbolic_weights = _resolve_feature_weights(
        config_versions,
        prefix=SYMBOLIC_FEATURE_WEIGHT_PREFIX,
        feature_keys=SYMBOLIC_FEATURE_WEIGHT_KEYS,
    )

    out_of_range_count = 0
    aggregated_entries: list[MeaningMatchEntry] = []
    calculated_at = datetime.now(UTC)

    for entry in feature_match_result.entries:
        _validate_feature_axes(entry)
        matching_config_id = entry.matching_config_id or default_matching_config_id
        if not matching_config_id:
            raise MeaningMatchAggregatorError(
                "matching_config_id is required for meaning match aggregation",
            )

        clipped_matches: dict[str, float] = {}
        for feature_code in MVP_FEATURE_CODES:
            axis = entry.features.get(feature_code)
            if axis is None:
                raise MeaningMatchAggregatorError(
                    f"missing feature match for axis: {feature_code}",
                )
            clipped, clipped_count = _clip_match(axis.match)
            clipped_matches[feature_code] = clipped
            out_of_range_count += clipped_count

        social_match = _weighted_average(
            clipped_matches,
            social_weights,
            SOCIAL_FEATURE_WEIGHT_KEYS,
        )
        symbolic_match = _weighted_average(
            clipped_matches,
            symbolic_weights,
            SYMBOLIC_FEATURE_WEIGHT_KEYS,
        )

        aggregated_entries.append(
            MeaningMatchEntry(
                item_id=entry.item_id,
                social_match=_round_match(social_match),
                symbolic_match=_round_match(symbolic_match),
                aggregation_method=AGGREGATION_METHOD_WEIGHTED_AVERAGE,
                calculated_at=calculated_at,
                matching_config_id=matching_config_id,
            ),
        )

    if feature_match_result.total_matched != len(feature_match_result.entries):
        raise MeaningMatchAggregatorError(
            "feature_match_result.total_matched is inconsistent with entries length",
        )

    result = MeaningMatchResult(
        entries=tuple(aggregated_entries),
        total_aggregated=len(aggregated_entries),
    )
    metrics = MeaningMatchAggregatorRunMetrics(
        meaning_match_aggregator_candidate_count=len(aggregated_entries),
        meaning_match_aggregator_latency_ms=0,
        meaning_match_value_out_of_range_count=out_of_range_count,
    )
    return result, metrics


def _resolve_feature_weights(
    config_versions: dict[str, str],
    *,
    prefix: str,
    feature_keys: tuple[str, ...],
) -> dict[str, float]:
    weights: dict[str, float] = {}
    for feature_code in feature_keys:
        raw = config_versions.get(f"{prefix}.{feature_code}")
        if raw is None:
            raise MeaningMatchAggregatorError(
                f"{prefix}.{feature_code} is required on execution_context.config_versions",
            )
        try:
            weights[feature_code] = float(raw)
        except ValueError as exc:
            raise MeaningMatchAggregatorError(
                f"invalid weight for {prefix}.{feature_code}: {raw!r}",
            ) from exc
    return weights


def _validate_feature_axes(entry: FeatureMatchEntry) -> None:
    for feature_code in MVP_FEATURE_CODES:
        if feature_code not in entry.features:
            raise MeaningMatchAggregatorError(
                f"missing feature match for axis: {feature_code}",
            )
        if entry.features[feature_code].match is None:
            raise MeaningMatchAggregatorError(
                f"feature match value is required for axis: {feature_code}",
            )


def _clip_match(value: float) -> tuple[float, int]:
    if value < GUARD_CLIP_MIN:
        return GUARD_CLIP_MIN, 1
    if value > GUARD_CLIP_MAX:
        return GUARD_CLIP_MAX, 1
    return value, 0


def _weighted_average(
    matches: dict[str, float],
    weights: dict[str, float],
    feature_keys: tuple[str, ...],
) -> float:
    weighted_sum = 0.0
    weight_sum = 0.0
    for feature_code in feature_keys:
        weight = weights[feature_code]
        weighted_sum += weight * matches[feature_code]
        weight_sum += weight
    if weight_sum == 0.0:
        return 0.0
    return weighted_sum / weight_sum


def _round_match(value: float) -> float:
    return round(value, MATCH_VALUE_DECIMAL_PLACES)
