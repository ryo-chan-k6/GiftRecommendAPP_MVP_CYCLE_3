"""Social / Symbolic projection for MOD-RECO-008."""

from __future__ import annotations

import math
from dataclasses import dataclass

from reco.domain.gift_meaning.features import (
    FEATURE_VALUE_MAX,
    FEATURE_VALUE_MIN,
    MVP_FEATURE_CODES,
    SOCIAL_FEATURE_CODES,
    SYMBOLIC_FEATURE_CODES,
)

from .constants import (
    GUARD_CLIP_MAX,
    GUARD_CLIP_MIN,
    PROJECTION_VALUE_DECIMAL_PLACES,
)
from .errors import UserMeaningProjectionError
from .models import MeaningProjectionWeights


@dataclass(frozen=True)
class ProjectionStats:
    """Run-scoped projection diagnostics for logging."""

    guard_clip_applied_count: int


_SOCIAL_WEIGHT_FIELDS: tuple[tuple[str, str], ...] = (
    ("formality", "w_formality"),
    ("safety", "w_safety"),
    ("brand_appropriateness", "w_brand_appropriateness"),
)

_SYMBOLIC_WEIGHT_FIELDS: tuple[tuple[str, str], ...] = (
    ("emotion", "w_emotion"),
    ("novelty", "w_novelty"),
    ("intimacy", "w_intimacy"),
    ("symbolic_identity", "w_symbolic_identity"),
    ("story_richness", "w_story_richness"),
)


def ensure_complete_normalized_features(features: dict[str, float]) -> dict[str, float]:
    missing = [code for code in MVP_FEATURE_CODES if code not in features]
    if missing:
        raise UserMeaningProjectionError(
            f"user_feature.features missing axes: {', '.join(missing)}",
        )

    normalized: dict[str, float] = {}
    for axis in MVP_FEATURE_CODES:
        value = float(features[axis])
        if math.isnan(value) or math.isinf(value):
            raise UserMeaningProjectionError(
                f"user_feature.features has non-finite value for axis {axis}",
            )
        if value < FEATURE_VALUE_MIN or value > FEATURE_VALUE_MAX:
            raise UserMeaningProjectionError(
                f"user_feature.features out of range for axis {axis}: {value}",
            )
        normalized[axis] = value
    return normalized


def guard_clip(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


def round_to_scale(value: float, decimal_places: int) -> float:
    return round(value, decimal_places)


def _axis_weights(
    weight_fields: tuple[tuple[str, str], ...],
    weights: MeaningProjectionWeights,
) -> list[float | None]:
    weight_by_field = {
        field_name: getattr(weights, field_name)
        for _, field_name in weight_fields
    }
    return [weight_by_field[field_name] for _, field_name in weight_fields]


def _project_group(
    features: dict[str, float],
    axes: tuple[str, ...],
    axis_weights: list[float | None],
) -> float:
    if len(axes) != len(axis_weights):
        raise UserMeaningProjectionError("projection axis/weight length mismatch")

    if all(weight is None for weight in axis_weights):
        return sum(features[axis] for axis in axes) / len(axes)

    effective_weights = [1.0 if weight is None else float(weight) for weight in axis_weights]
    weight_sum = sum(effective_weights)
    if weight_sum <= 0:
        raise UserMeaningProjectionError("projection weight sum must be positive")

    weighted_sum = sum(
        effective_weights[index] * features[axes[index]]
        for index in range(len(axes))
    )
    return weighted_sum / weight_sum


def _finalize_projection_value(raw_value: float) -> tuple[float, bool]:
    if math.isnan(raw_value) or math.isinf(raw_value):
        raise UserMeaningProjectionError("projection produced non-finite value")

    guard_clip_applied = raw_value < GUARD_CLIP_MIN or raw_value > GUARD_CLIP_MAX
    clipped = guard_clip(raw_value, GUARD_CLIP_MIN, GUARD_CLIP_MAX)
    return round_to_scale(clipped, PROJECTION_VALUE_DECIMAL_PLACES), guard_clip_applied


def project_user_meaning_coordinates(
    features: dict[str, float],
    weights: MeaningProjectionWeights,
) -> tuple[float, float, ProjectionStats]:
    """Apply GiftMeaningSpace §5.2 / §5.3 weighted-average projection."""
    normalized_features = ensure_complete_normalized_features(features)

    social_raw = _project_group(
        normalized_features,
        SOCIAL_FEATURE_CODES,
        _axis_weights(_SOCIAL_WEIGHT_FIELDS, weights),
    )
    symbolic_raw = _project_group(
        normalized_features,
        SYMBOLIC_FEATURE_CODES,
        _axis_weights(_SYMBOLIC_WEIGHT_FIELDS, weights),
    )

    user_social, social_clip = _finalize_projection_value(social_raw)
    user_symbolic, symbolic_clip = _finalize_projection_value(symbolic_raw)

    return user_social, user_symbolic, ProjectionStats(
        guard_clip_applied_count=int(social_clip) + int(symbolic_clip),
    )
