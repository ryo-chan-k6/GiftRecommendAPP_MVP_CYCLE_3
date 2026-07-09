"""Scaffold wiring helpers for MOD-RECO-023."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .executor import ReasonGenerator, build_default_reason_generator


def build_scaffold_reason_generator() -> ReasonGenerator:
    """Build Reason Generator for MVP scaffold wiring."""
    return ReasonGenerator(logger=ScaffoldRecoLogger())


__all__ = [
    "ReasonGenerator",
    "build_default_reason_generator",
    "build_scaffold_reason_generator",
]
