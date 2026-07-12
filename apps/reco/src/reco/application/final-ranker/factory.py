"""Scaffold wiring helpers for MOD-RECO-020."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .executor import FinalRanker, build_default_final_ranker


def build_scaffold_final_ranker() -> FinalRanker:
    """Build Final Ranker for MVP scaffold wiring."""
    return FinalRanker(logger=ScaffoldRecoLogger())


__all__ = [
    "FinalRanker",
    "build_default_final_ranker",
    "build_scaffold_final_ranker",
]
