"""Scaffold wiring helpers for MOD-RECO-016."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .executor import ContextScorer, build_default_context_scorer


def build_scaffold_context_scorer() -> ContextScorer:
    """Build Context Scorer for MVP scaffold wiring."""
    return ContextScorer(logger=ScaffoldRecoLogger())


__all__ = [
    "ContextScorer",
    "build_default_context_scorer",
    "build_scaffold_context_scorer",
]
