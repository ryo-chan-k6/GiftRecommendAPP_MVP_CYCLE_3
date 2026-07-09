"""Scaffold wiring helpers for MOD-RECO-024."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .executor import RecoErrorHandler, build_default_reco_error_handler


def build_scaffold_reco_error_handler() -> RecoErrorHandler:
    """Build Reco Error Handler for MVP scaffold wiring."""
    return RecoErrorHandler(logger=ScaffoldRecoLogger())


__all__ = [
    "RecoErrorHandler",
    "build_default_reco_error_handler",
    "build_scaffold_reco_error_handler",
]
