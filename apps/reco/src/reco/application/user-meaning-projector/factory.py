"""Scaffold wiring helpers for MOD-RECO-008."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .in_memory_repository import (
    InMemoryMeaningProjectionConfigRepository,
    InMemoryRunValidation,
    InMemoryUserFeatureReadRepository,
    build_default_in_memory_repositories,
    build_default_projection_weights,
)
from .projector import UserMeaningProjector, build_default_user_meaning_projector


def build_scaffold_user_meaning_projector() -> UserMeaningProjector:
    """Build projector backed by in-memory repositories (MVP scaffold)."""
    projection_config = InMemoryMeaningProjectionConfigRepository(
        weights=build_default_projection_weights(),
    )
    user_features = InMemoryUserFeatureReadRepository()
    run_validation = InMemoryRunValidation()
    return UserMeaningProjector(
        projection_config=projection_config,
        user_features=user_features,
        run_validation=run_validation,
        logger=ScaffoldRecoLogger(),
    )


__all__ = [
    "InMemoryMeaningProjectionConfigRepository",
    "InMemoryRunValidation",
    "InMemoryUserFeatureReadRepository",
    "UserMeaningProjector",
    "build_default_in_memory_repositories",
    "build_default_projection_weights",
    "build_default_user_meaning_projector",
    "build_scaffold_user_meaning_projector",
]
