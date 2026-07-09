"""Scaffold wiring helpers for MOD-RECO-022."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .executor import ResultSnapshotBuilder, build_default_result_snapshot_builder


def build_scaffold_result_snapshot_builder() -> ResultSnapshotBuilder:
    """Build Result Snapshot Builder for MVP scaffold wiring."""
    return ResultSnapshotBuilder(logger=ScaffoldRecoLogger())


__all__ = [
    "ResultSnapshotBuilder",
    "build_default_result_snapshot_builder",
    "build_scaffold_result_snapshot_builder",
]
