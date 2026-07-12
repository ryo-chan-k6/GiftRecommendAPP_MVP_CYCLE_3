"""Feature から Social / Symbolic 座標への射影。"""

from typing import Iterable, Mapping

from gift_recommendation.shared_logic.catalog import load_mvp_feature_codes
from gift_recommendation.shared_logic.constants import (
    FEATURE_VALUE_MAX,
    FEATURE_VALUE_MIN,
    SOCIAL_FEATURE_CODES,
    SYMBOLIC_FEATURE_CODES,
)
from gift_recommendation.shared_logic.feature_engine import validate_complete_feature_vector
from gift_recommendation.shared_logic.types import FeatureVector, MeaningCoordinates, ProjectionWeights


def _weighted_average(
    vector: Mapping[str, float],
    codes: Iterable[str],
    weights: Mapping[str, float],
) -> float:
    total_weight = 0.0
    weighted_sum = 0.0

    for code in codes:
        weight = float(weights.get(code, 1.0))
        total_weight += weight
        weighted_sum += weight * float(vector[code])

    if total_weight == 0.0:
        return 0.0

    return clip_coordinate(weighted_sum / total_weight)


def clip_coordinate(value: float) -> float:
    return max(FEATURE_VALUE_MIN, min(FEATURE_VALUE_MAX, value))


def project_to_meaning(
    normalized_vector: Mapping[str, float],
    *,
    weights: ProjectionWeights | None = None,
    feature_codes: Iterable[str] | None = None,
) -> MeaningCoordinates:
    """正規化済み Feature から Gift Meaning Space 座標を算出する。"""
    codes = tuple(feature_codes) if feature_codes is not None else load_mvp_feature_codes()
    validate_complete_feature_vector(normalized_vector, feature_codes=codes)

    weight_map = (weights or ProjectionWeights()).as_mapping()

    social = _weighted_average(normalized_vector, SOCIAL_FEATURE_CODES, weight_map)
    symbolic = _weighted_average(normalized_vector, SYMBOLIC_FEATURE_CODES, weight_map)

    return MeaningCoordinates(social=social, symbolic=symbolic)
