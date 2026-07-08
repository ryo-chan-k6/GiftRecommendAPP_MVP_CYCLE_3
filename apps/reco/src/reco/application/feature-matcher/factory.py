"""Scaffold wiring helpers for MOD-RECO-014."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .executor import FeatureMatcher, build_default_feature_matcher
from .in_memory_repository import build_default_in_memory_repositories


def build_scaffold_feature_matcher() -> FeatureMatcher:
    """Build Feature Matcher backed by in-memory repositories (MVP scaffold)."""
    item_features, normalization = build_default_in_memory_repositories()
    return FeatureMatcher(
        item_feature_repository=item_features,
        normalization=normalization,
        logger=ScaffoldRecoLogger(),
    )


__all__ = [
    "FeatureMatcher",
    "build_default_feature_matcher",
    "build_scaffold_feature_matcher",
]
