"""Scaffold wiring helpers for MOD-RECO-019."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .executor import FinalScoreCalculator, build_default_final_score_calculator


def build_scaffold_final_score_calculator() -> FinalScoreCalculator:
    """Build Final Score Calculator for MVP scaffold wiring."""
    return FinalScoreCalculator(logger=ScaffoldRecoLogger())


__all__ = [
    "FinalScoreCalculator",
    "build_default_final_score_calculator",
    "build_scaffold_final_score_calculator",
]
