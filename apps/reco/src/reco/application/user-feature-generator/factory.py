"""Scaffold wiring helpers for MOD-RECO-007."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .generator import UserFeatureGenerator, build_default_user_feature_generator
from .in_memory_repository import (
    InMemoryNormalizationRuleRepository,
    InMemoryRunValidation,
    InMemoryUserFeatureRepository,
    build_default_in_memory_repositories,
    build_default_normalization_binding,
    build_default_user_feature_repository,
)


def build_scaffold_user_feature_generator() -> UserFeatureGenerator:
    """Build generator backed by in-memory repositories (MVP scaffold)."""
    normalization_rules = InMemoryNormalizationRuleRepository(
        binding=build_default_normalization_binding(),
    )
    user_features = InMemoryUserFeatureRepository()
    run_validation = InMemoryRunValidation()
    return UserFeatureGenerator(
        normalization_rules=normalization_rules,
        user_features=user_features,
        run_validation=run_validation,
        logger=ScaffoldRecoLogger(),
    )


__all__ = [
    "InMemoryNormalizationRuleRepository",
    "InMemoryRunValidation",
    "InMemoryUserFeatureRepository",
    "UserFeatureGenerator",
    "build_default_in_memory_repositories",
    "build_default_normalization_binding",
    "build_default_user_feature_generator",
    "build_default_user_feature_repository",
    "build_scaffold_user_feature_generator",
]
