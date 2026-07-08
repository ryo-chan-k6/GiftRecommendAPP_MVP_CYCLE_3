"""Scaffold wiring helpers for MOD-RECO-018."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .executor import RiskScorer, build_default_risk_scorer


def build_scaffold_risk_scorer() -> RiskScorer:
    """Build Risk Scorer for MVP scaffold wiring."""
    return RiskScorer(logger=ScaffoldRecoLogger())


__all__ = [
    "RiskScorer",
    "build_default_risk_scorer",
    "build_scaffold_risk_scorer",
]
