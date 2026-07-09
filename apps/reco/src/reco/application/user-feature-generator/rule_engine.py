"""User Feature raw merge and sigmoid normalization for MOD-RECO-007."""

from __future__ import annotations

import math
from dataclasses import dataclass

from reco.domain.gift_meaning.features import FEATURE_VALUE_MAX, FEATURE_VALUE_MIN, MVP_FEATURE_CODES

from .constants import (
    FEATURE_VALUE_DECIMAL_PLACES,
    GUARD_CLIP_MAX,
    GUARD_CLIP_MIN,
)
from .errors import UserFeatureGenerationError
from .models import FeatureNormalizationParameters


@dataclass(frozen=True)
class NormalizationStats:
    """Run-scoped normalization diagnostics for logging."""

    raw_out_of_range_count: int
    guard_clip_applied_count: int


def ensure_complete_feature_vector(
    values: dict[str, float],
    *,
    vector_name: str,
) -> dict[str, float]:
    missing = [code for code in MVP_FEATURE_CODES if code not in values]
    if missing:
        raise UserFeatureGenerationError(
            f"{vector_name} missing axes: {', '.join(missing)}",
        )
    return {code: float(values[code]) for code in MVP_FEATURE_CODES}


def merge_user_feature_raw(
    external_feature_raw: dict[str, float],
    internal_feature_delta: dict[str, float],
) -> dict[str, float]:
    """Featureルール定義書 §12.2: external raw + internal delta per axis."""
    external = ensure_complete_feature_vector(
        external_feature_raw,
        vector_name="external_feature_raw",
    )
    internal = ensure_complete_feature_vector(
        internal_feature_delta,
        vector_name="internal_feature_delta",
    )
    return {
        axis: external[axis] + internal[axis]
        for axis in MVP_FEATURE_CODES
    }


def sigmoid(x: float) -> float:
    if math.isnan(x):
        return float("nan")
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    exp_x = math.exp(x)
    return exp_x / (1.0 + exp_x)


def guard_clip(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


def round_to_scale(value: float, decimal_places: int) -> float:
    return round(value, decimal_places)


def normalize_user_features(
    user_feature_raw: dict[str, float],
    parameters: FeatureNormalizationParameters,
) -> tuple[dict[str, float], NormalizationStats]:
    """Apply sigmoid normalization and guard_clip per Featureルール定義書 §14."""
    if parameters.normalization_method != "sigmoid":
        raise UserFeatureGenerationError(
            f"unsupported normalization_method: {parameters.normalization_method}",
        )

    normalized: dict[str, float] = {}
    raw_out_of_range_count = 0
    guard_clip_applied_count = 0

    for axis in MVP_FEATURE_CODES:
        raw_value = float(user_feature_raw[axis])
        if raw_value < FEATURE_VALUE_MIN or raw_value > FEATURE_VALUE_MAX:
            raw_out_of_range_count += 1

        sigmoid_input = parameters.k_feature * (raw_value - parameters.center_feature)
        sigmoid_value = sigmoid(sigmoid_input)
        if math.isnan(sigmoid_value) or math.isinf(sigmoid_value):
            raise UserFeatureGenerationError(
                f"sigmoid produced non-finite value for axis {axis}",
            )

        if sigmoid_value < GUARD_CLIP_MIN or sigmoid_value > GUARD_CLIP_MAX:
            guard_clip_applied_count += 1

        clipped = guard_clip(sigmoid_value, GUARD_CLIP_MIN, GUARD_CLIP_MAX)
        normalized[axis] = round_to_scale(clipped, FEATURE_VALUE_DECIMAL_PLACES)

    return normalized, NormalizationStats(
        raw_out_of_range_count=raw_out_of_range_count,
        guard_clip_applied_count=guard_clip_applied_count,
    )
