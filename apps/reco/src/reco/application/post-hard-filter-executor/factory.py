"""Scaffold wiring helpers for MOD-RECO-013."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .executor import PostHardFilterExecutor, build_default_post_hard_filter_executor
from .in_memory_repository import build_default_in_memory_item_repository


def build_scaffold_post_hard_filter_executor() -> PostHardFilterExecutor:
    """Build Post Hard Filter Executor backed by in-memory repository (MVP scaffold)."""
    return PostHardFilterExecutor(
        item_repository=build_default_in_memory_item_repository(),
        logger=ScaffoldRecoLogger(),
    )


__all__ = [
    "PostHardFilterExecutor",
    "build_default_post_hard_filter_executor",
    "build_scaffold_post_hard_filter_executor",
]
