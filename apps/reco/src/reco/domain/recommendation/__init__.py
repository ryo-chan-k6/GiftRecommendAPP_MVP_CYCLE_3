"""Recommendation aggregate scaffold."""

from reco.domain.recommendation.inputs import (
    BudgetCondition,
    ExecutionCondition,
    ExecutionMode,
    NgCondition,
    NonPreferredCondition,
    OccasionCondition,
    PreferredCondition,
    RelationshipCondition,
)
from reco.domain.recommendation.request import RecommendationRequest
from reco.domain.recommendation.result import RecommendationResult, RecommendationResultItem
from reco.domain.recommendation.result import ReasonStatus, ResultStatus
from reco.domain.recommendation.run import RecommendationRun, RunStatus

__all__ = [
    "BudgetCondition",
    "ExecutionCondition",
    "ExecutionMode",
    "NgCondition",
    "NonPreferredCondition",
    "OccasionCondition",
    "PreferredCondition",
    "RecommendationRequest",
    "RecommendationResult",
    "RecommendationResultItem",
    "ReasonStatus",
    "ResultStatus",
    "RecommendationRun",
    "RelationshipCondition",
    "RunStatus",
]
