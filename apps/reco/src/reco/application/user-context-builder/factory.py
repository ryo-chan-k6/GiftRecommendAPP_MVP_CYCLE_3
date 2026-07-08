"""Scaffold wiring helpers for MOD-RECO-009."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .builder import UserContextBuilder, build_default_user_context_builder
from .in_memory_repository import (
    InMemoryLambdaContextRuleRepository,
    InMemoryRunValidation,
    InMemoryUserFeatureReadRepository,
    InMemoryUserMeaningRepository,
    build_default_in_memory_repositories,
)


def build_scaffold_user_context_builder() -> UserContextBuilder:
    """Build User Context Builder backed by in-memory repositories (MVP scaffold)."""
    lambda_ctx_rules, user_meaning_repo, user_features, run_validation = (
        build_default_in_memory_repositories()
    )
    return UserContextBuilder(
        lambda_ctx_rules=lambda_ctx_rules,
        user_meaning_repo=user_meaning_repo,
        user_features=user_features,
        run_validation=run_validation,
        logger=ScaffoldRecoLogger(),
    )


__all__ = [
    "InMemoryLambdaContextRuleRepository",
    "InMemoryRunValidation",
    "InMemoryUserFeatureReadRepository",
    "InMemoryUserMeaningRepository",
    "UserContextBuilder",
    "build_default_in_memory_repositories",
    "build_default_user_context_builder",
    "build_scaffold_user_context_builder",
]
