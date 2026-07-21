"""Scaffold wiring helpers for MOD-RECO-015."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .executor import MeaningMatchAggregator, build_default_meaning_match_aggregator


def build_scaffold_meaning_match_aggregator() -> MeaningMatchAggregator:
    """Build Meaning Match Aggregator for MVP scaffold wiring."""
    return MeaningMatchAggregator(logger=ScaffoldRecoLogger())


__all__ = [
    "MeaningMatchAggregator",
    "build_default_meaning_match_aggregator",
    "build_scaffold_meaning_match_aggregator",
]
