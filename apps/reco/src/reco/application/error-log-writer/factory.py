"""Scaffold wiring helpers for MOD-RECO-029."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .writer import ErrorLogWriter, build_default_error_log_writer


def build_scaffold_error_log_writer() -> ErrorLogWriter:
    """Build Error Log Writer for MVP scaffold wiring."""
    return ErrorLogWriter(logger=ScaffoldRecoLogger())


__all__ = [
    "ErrorLogWriter",
    "build_default_error_log_writer",
    "build_scaffold_error_log_writer",
]
