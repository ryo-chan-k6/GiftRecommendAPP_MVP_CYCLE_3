"""Reco recommendation domain core scaffold (Phase4a)."""

from reco.domain.gift_meaning.features import (
    FEATURE_VALUE_MAX,
    FEATURE_VALUE_MIN,
    MVP_FEATURE_CODES,
    SOCIAL_FEATURE_CODES,
    SYMBOLIC_FEATURE_CODES,
    FeatureVector,
)
from reco.domain.matching.score import MatchingScore
from reco.domain.recommendation.request import RecommendationRequest
from reco.domain.recommendation.result import RecommendationResult, RecommendationResultItem
from reco.domain.recommendation.run import RecommendationRun, RunStatus

__all__ = [
    "FEATURE_VALUE_MAX",
    "FEATURE_VALUE_MIN",
    "MVP_FEATURE_CODES",
    "MatchingScore",
    "RecommendationRequest",
    "RecommendationResult",
    "RecommendationResultItem",
    "RecommendationRun",
    "RunStatus",
    "SOCIAL_FEATURE_CODES",
    "SYMBOLIC_FEATURE_CODES",
    "FeatureVector",
]
