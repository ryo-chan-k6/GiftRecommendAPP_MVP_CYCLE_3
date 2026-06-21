"""Recommendation aggregate scaffold."""

from reco.domain.recommendation.request import RecommendationRequest
from reco.domain.recommendation.result import RecommendationResult, RecommendationResultItem
from reco.domain.recommendation.run import RecommendationRun, RunStatus

__all__ = [
    "RecommendationRequest",
    "RecommendationResult",
    "RecommendationResultItem",
    "RecommendationRun",
    "RunStatus",
]
