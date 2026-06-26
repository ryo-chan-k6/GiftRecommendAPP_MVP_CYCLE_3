"""Scaffold wiring helpers for MOD-RECO-004."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .extractor import UserSemanticExtractor, build_default_user_semantic_extractor
from .in_memory_repository import (
    InMemoryRunValidation,
    InMemorySemanticCatalog,
    InMemoryUserSemanticRepository,
    build_default_in_memory_repositories,
    build_default_semantic_catalog,
)


def build_scaffold_user_semantic_extractor(
    *,
    should_fail_insert: bool = False,
) -> UserSemanticExtractor:
    """Build extractor backed by in-memory repositories (MVP scaffold)."""
    catalog = build_default_semantic_catalog()
    run_validation = InMemoryRunValidation()
    user_semantic_repo = InMemoryUserSemanticRepository(
        should_fail_on_insert=should_fail_insert,
    )
    return UserSemanticExtractor(
        catalog=catalog,
        run_validation=run_validation,
        user_semantic_repository=user_semantic_repo,
        logger=ScaffoldRecoLogger(),
    )


__all__ = [
    "InMemoryRunValidation",
    "InMemorySemanticCatalog",
    "InMemoryUserSemanticRepository",
    "UserSemanticExtractor",
    "build_default_in_memory_repositories",
    "build_default_user_semantic_extractor",
    "build_scaffold_user_semantic_extractor",
]
