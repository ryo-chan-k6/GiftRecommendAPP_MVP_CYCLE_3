"""Scaffold wiring helpers for MOD-RECO-021."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .executor import (
    RecommendationResultBuilder,
    build_default_recommendation_result_builder,
)


def build_scaffold_recommendation_result_builder() -> RecommendationResultBuilder:
    """Build Recommendation Result Builder for MVP scaffold wiring."""
    return RecommendationResultBuilder(logger=ScaffoldRecoLogger())


__all__ = [
    "RecommendationResultBuilder",
    "build_default_recommendation_result_builder",
    "build_scaffold_recommendation_result_builder",
]
