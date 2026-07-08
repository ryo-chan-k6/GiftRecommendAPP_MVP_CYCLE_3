"""Rule lookup and external condition raw integration for MOD-RECO-005."""

from __future__ import annotations

from reco.domain.gift_meaning.features import MVP_FEATURE_CODES

from .constants import DEFAULT_OCCASION_WEIGHT, DEFAULT_RELATIONSHIP_WEIGHT
from .errors import ExternalFeatureEstimateError
from .models import FeatureIntegrationWeights, FeatureVector


def zero_feature_vector() -> dict[str, float]:
    return {code: 0.0 for code in MVP_FEATURE_CODES}


def ensure_complete_feature_vector(
    values: FeatureVector,
    *,
    rule_kind: str,
    code: str,
) -> dict[str, float]:
    resolved = {code: float(values[code]) for code in MVP_FEATURE_CODES if code in values}
    missing = [code for code in MVP_FEATURE_CODES if code not in resolved]
    if missing:
        raise ExternalFeatureEstimateError(
            f"{rule_kind} rule missing axes for {code}: {', '.join(missing)}",
        )
    return resolved


def merge_external_feature_raw(
    relationship_feature: FeatureVector,
    occasion_feature: FeatureVector,
    pair_delta: FeatureVector,
    *,
    weights: FeatureIntegrationWeights | None = None,
) -> dict[str, float]:
    """Featureルール定義書 §12.2: weighted average + pair_delta."""
    relationship_weight = (
        weights.relationship_weight if weights is not None else DEFAULT_RELATIONSHIP_WEIGHT
    )
    occasion_weight = (
        weights.occasion_weight if weights is not None else DEFAULT_OCCASION_WEIGHT
    )
    return {
        axis: (
            relationship_weight * float(relationship_feature[axis])
            + occasion_weight * float(occasion_feature[axis])
            + float(pair_delta[axis])
        )
        for axis in MVP_FEATURE_CODES
    }
