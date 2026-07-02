"""Feature distance / match calculation for MOD-RECO-014."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from reco.application.user_feature_generator.rule_engine import (
    guard_clip,
    round_to_scale,
    sigmoid,
)
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES

from .constants import (
    AVOID_FEATURE_BASELINE,
    FEATURE_VALUE_DECIMAL_PLACES,
    GUARD_CLIP_MAX,
    GUARD_CLIP_MIN,
    IMPUTED_FEATURE_VALUE,
    MATCH_METHOD_ONE_MINUS_DISTANCE,
)
from .errors import FeatureMatcherError
from .models import (
    FeatureAxisMatch,
    FeatureMatchEntry,
    FeatureMatchResult,
    FeatureMatcherRunMetrics,
)
from .ports import FeatureNormalizationPort, ItemFeatureRepositoryPort

if TYPE_CHECKING:
    from reco.application.internal_condition_feature_estimator.models import (
        InternalFeatureEstimate,
    )
    from reco.application.post_hard_filter_executor.models import (
        ValidatedRetrievalCandidate,
    )
    from reco.application.user_feature_generator.models import UserFeature


def run_feature_matching(
    *,
    user_feature: UserFeature,
    internal_feature_estimate: InternalFeatureEstimate,
    validated_retrieval_candidate: ValidatedRetrievalCandidate,
    semantic_config_version_id: str,
    matching_config_id: str,
    item_feature_repository: ItemFeatureRepositoryPort,
    normalization: FeatureNormalizationPort,
) -> tuple[FeatureMatchResult, FeatureMatcherRunMetrics]:
    """Execute Matching for validated candidates (§8.1〜§8.3)."""
    user_axes = _validate_user_feature_axes(user_feature)
    if validated_retrieval_candidate.total_validated == 0:
        return _empty_result(), _zero_metrics()

    item_ids = tuple(
        candidate.item_id for candidate in validated_retrieval_candidate.candidates
    )
    try:
        item_features_by_id = item_feature_repository.fetch_item_features(
            item_ids,
            semantic_config_version_id,
        )
    except Exception as exc:  # noqa: BLE001 — DB 障害を GRS-REC-011 へ集約
        raise FeatureMatcherError(
            "item_feature repository fetch failed",
        ) from exc

    non_preferred, has_avoid_signal = _build_non_preferred_vector(
        internal_feature_estimate.avoid_delta,
        user_feature.feature_normalization_version_id,
        normalization,
    )

    entries: list[FeatureMatchEntry] = []
    total_excluded = 0
    total_imputed_axes = 0
    total_out_of_range = 0
    calculated_at = datetime.now(UTC)

    for candidate in validated_retrieval_candidate.candidates:
        item_axes = item_features_by_id.get(candidate.item_id)
        if not item_axes:
            total_excluded += 1
            continue

        resolved = _resolve_item_axes(item_axes)
        if resolved is None:
            total_excluded += 1
            continue

        total_imputed_axes += resolved.imputed_axis_count
        total_out_of_range += resolved.out_of_range_count
        resolved_item_axes = resolved.values

        feature_results: dict[str, FeatureAxisMatch] = {}
        squared_diff_sum = 0.0
        for axis in MVP_FEATURE_CODES:
            user_value = user_axes[axis]
            item_value = resolved_item_axes[axis]
            distance = abs(user_value - item_value)
            match = 1.0 - distance
            feature_results[axis] = FeatureAxisMatch(
                distance=round_to_scale(distance, FEATURE_VALUE_DECIMAL_PLACES),
                match=round_to_scale(match, FEATURE_VALUE_DECIMAL_PLACES),
                match_method=MATCH_METHOD_ONE_MINUS_DISTANCE,
                imputed=resolved.imputed_axes.get(axis, False),
            )
            squared_diff_sum += (user_value - item_value) ** 2

        meaning_distance = math.sqrt(squared_diff_sum)
        avoid_similarity: float | None = None
        if has_avoid_signal:
            axis_matches = [
                1.0 - abs(non_preferred[axis] - resolved_item_axes[axis])
                for axis in MVP_FEATURE_CODES
            ]
            avoid_similarity = round_to_scale(
                sum(axis_matches) / len(axis_matches),
                FEATURE_VALUE_DECIMAL_PLACES,
            )

        entries.append(
            FeatureMatchEntry(
                item_id=candidate.item_id,
                features=feature_results,
                meaning_distance=round_to_scale(
                    meaning_distance,
                    FEATURE_VALUE_DECIMAL_PLACES,
                ),
                calculated_at=calculated_at,
                matching_config_id=matching_config_id,
                avoid_similarity=avoid_similarity,
            ),
        )

    result = FeatureMatchResult(
        entries=tuple(entries),
        total_matched=len(entries),
        total_excluded=total_excluded,
    )
    metrics = FeatureMatcherRunMetrics(
        feature_matcher_candidate_count=len(entries),
        feature_matcher_excluded_count=total_excluded,
        feature_matcher_latency_ms=0,
        feature_match_imputed_axis_count=total_imputed_axes,
        feature_value_out_of_range_count=total_out_of_range,
    )
    return result, metrics


def _validate_user_feature_axes(user_feature: UserFeature) -> dict[str, float]:
    missing = [code for code in MVP_FEATURE_CODES if code not in user_feature.features]
    if missing:
        raise FeatureMatcherError(
            f"user_feature missing axes: {', '.join(missing)}",
        )
    return {code: float(user_feature.features[code]) for code in MVP_FEATURE_CODES}


def _build_non_preferred_vector(
    avoid_delta: dict[str, float],
    feature_normalization_version_id: str,
    normalization: FeatureNormalizationPort,
) -> tuple[dict[str, float], bool]:
    has_avoid_signal = any(
        float(avoid_delta.get(axis, 0.0)) != 0.0 for axis in MVP_FEATURE_CODES
    )
    if not has_avoid_signal:
        return {}, False

    parameters = normalization.get_parameters(feature_normalization_version_id)
    if parameters is None:
        raise FeatureMatcherError(
            f"normalization parameters not found: {feature_normalization_version_id}",
        )
    if parameters.normalization_method != "sigmoid":
        raise FeatureMatcherError(
            f"unsupported normalization_method: {parameters.normalization_method}",
        )

    non_preferred: dict[str, float] = {}
    for axis in MVP_FEATURE_CODES:
        raw_value = AVOID_FEATURE_BASELINE + float(avoid_delta.get(axis, 0.0))
        sigmoid_input = parameters.k_feature * (raw_value - parameters.center_feature)
        sigmoid_value = sigmoid(sigmoid_input)
        if math.isnan(sigmoid_value) or math.isinf(sigmoid_value):
            raise FeatureMatcherError(
                f"sigmoid produced non-finite value for avoid axis {axis}",
            )
        clipped = guard_clip(sigmoid_value, GUARD_CLIP_MIN, GUARD_CLIP_MAX)
        non_preferred[axis] = round_to_scale(clipped, FEATURE_VALUE_DECIMAL_PLACES)
    return non_preferred, True


@dataclass(frozen=True)
class _ResolvedItemAxes:
    values: dict[str, float]
    imputed_axes: dict[str, bool]
    imputed_axis_count: int
    out_of_range_count: int


def _resolve_item_axes(item_axes: dict[str, float]) -> _ResolvedItemAxes | None:
    if not item_axes:
        return None

    resolved: dict[str, float] = {}
    imputed_axes: dict[str, bool] = {}
    imputed_axis_count = 0
    out_of_range_count = 0

    for axis in MVP_FEATURE_CODES:
        if axis not in item_axes:
            resolved[axis] = IMPUTED_FEATURE_VALUE
            imputed_axes[axis] = True
            imputed_axis_count += 1
            continue

        raw_value = float(item_axes[axis])
        if raw_value < GUARD_CLIP_MIN or raw_value > GUARD_CLIP_MAX:
            out_of_range_count += 1
        clipped = guard_clip(raw_value, GUARD_CLIP_MIN, GUARD_CLIP_MAX)
        resolved[axis] = round_to_scale(clipped, FEATURE_VALUE_DECIMAL_PLACES)
        imputed_axes[axis] = False

    return _ResolvedItemAxes(
        values=resolved,
        imputed_axes=imputed_axes,
        imputed_axis_count=imputed_axis_count,
        out_of_range_count=out_of_range_count,
    )


def _empty_result() -> FeatureMatchResult:
    return FeatureMatchResult(entries=(), total_matched=0, total_excluded=0)


def _zero_metrics() -> FeatureMatcherRunMetrics:
    return FeatureMatcherRunMetrics(
        feature_matcher_candidate_count=0,
        feature_matcher_excluded_count=0,
        feature_matcher_latency_ms=0,
        feature_match_imputed_axis_count=0,
        feature_value_out_of_range_count=0,
    )
