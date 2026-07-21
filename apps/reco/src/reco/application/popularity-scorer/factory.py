"""Scaffold wiring helpers for MOD-RECO-017."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .executor import PopularityScorer, build_default_popularity_scorer
from .in_memory_repository import (
    build_default_in_memory_item_review_summary_repository,
)


def build_scaffold_popularity_scorer() -> PopularityScorer:
    """Build Popularity Scorer for MVP scaffold wiring."""
    return PopularityScorer(
        review_summary_repository=build_default_in_memory_item_review_summary_repository(),
        logger=ScaffoldRecoLogger(),
    )


__all__ = [
    "PopularityScorer",
    "build_default_popularity_scorer",
    "build_scaffold_popularity_scorer",
]
