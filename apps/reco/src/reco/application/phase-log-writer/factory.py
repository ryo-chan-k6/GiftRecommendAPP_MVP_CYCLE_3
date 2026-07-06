"""Scaffold wiring helpers for MOD-RECO-028."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .writer import PhaseLogWriter, build_default_phase_log_writer


def build_scaffold_phase_log_writer() -> PhaseLogWriter:
    """Build Phase Log Writer for MVP scaffold wiring."""
    return PhaseLogWriter(logger=ScaffoldRecoLogger())


__all__ = [
    "PhaseLogWriter",
    "build_default_phase_log_writer",
    "build_scaffold_phase_log_writer",
]
