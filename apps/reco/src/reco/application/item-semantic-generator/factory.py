"""Scaffold wiring helpers for MOD-RECO-026."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .generator import ItemSemanticGenerator, build_default_item_semantic_generator
from .in_memory_repository import (
    InMemoryItemSemanticRepository,
    InMemoryItemValidation,
    InMemorySemanticCatalog,
    InMemorySemanticConfigVersion,
    build_default_in_memory_repositories,
    build_default_semantic_catalog,
)


def build_scaffold_item_semantic_generator(
    *,
    should_fail_upsert: bool = False,
) -> ItemSemanticGenerator:
    """Build generator backed by in-memory repositories (MVP scaffold)."""
    catalog = build_default_semantic_catalog()
    item_validation = InMemoryItemValidation()
    version_validation = InMemorySemanticConfigVersion()
    from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID

    version_validation.register_version(DEFAULT_SEMANTIC_CONFIG_VERSION_ID)
    item_semantic_repo = InMemoryItemSemanticRepository(
        should_fail_on_upsert=should_fail_upsert,
    )
    return ItemSemanticGenerator(
        catalog=catalog,
        item_validation=item_validation,
        semantic_config_version=version_validation,
        item_semantic_repository=item_semantic_repo,
        logger=ScaffoldRecoLogger(),
    )


__all__ = [
    "InMemoryItemSemanticRepository",
    "InMemoryItemValidation",
    "InMemorySemanticCatalog",
    "InMemorySemanticConfigVersion",
    "ItemSemanticGenerator",
    "build_default_in_memory_repositories",
    "build_default_item_semantic_generator",
    "build_scaffold_item_semantic_generator",
]
