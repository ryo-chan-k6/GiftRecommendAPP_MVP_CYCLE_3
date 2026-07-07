"""Scaffold wiring helpers for MOD-RECO-025."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .logger import MetricLogger, build_default_metric_logger


def build_scaffold_metric_logger() -> MetricLogger:
    """Build Metric Logger for MVP scaffold wiring."""
    return MetricLogger(logger=ScaffoldRecoLogger())


__all__ = [
    "MetricLogger",
    "build_default_metric_logger",
    "build_scaffold_metric_logger",
]
