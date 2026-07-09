"""reco / batch 共通ドメインロジック。"""

from gift_recommendation.shared_logic.catalog import (
    get_code_definitions_root,
    get_package_root,
    load_mvp_feature_codes,
)
from gift_recommendation.shared_logic.constants import (
    MVP_FEATURE_CODES,
    SOCIAL_FEATURE_CODES,
    SYMBOLIC_FEATURE_CODES,
)
from gift_recommendation.shared_logic.errors import IncompleteFeatureVectorError, SharedLogicError
from gift_recommendation.shared_logic.feature_engine import (
    clip_feature_vector,
    integrate_feature_deltas,
    validate_complete_feature_vector,
)
from gift_recommendation.shared_logic.meaning_projection import project_to_meaning
from gift_recommendation.shared_logic.normalization import NormalizationMethod, normalize_features
from gift_recommendation.shared_logic.types import FeatureVector, MeaningCoordinates, ProjectionWeights

__all__ = [
    "FeatureVector",
    "IncompleteFeatureVectorError",
    "MVP_FEATURE_CODES",
    "MeaningCoordinates",
    "NormalizationMethod",
    "ProjectionWeights",
    "SOCIAL_FEATURE_CODES",
    "SYMBOLIC_FEATURE_CODES",
    "SharedLogicError",
    "clip_feature_vector",
    "get_code_definitions_root",
    "get_package_root",
    "integrate_feature_deltas",
    "load_mvp_feature_codes",
    "normalize_features",
    "project_to_meaning",
    "validate_complete_feature_vector",
]
