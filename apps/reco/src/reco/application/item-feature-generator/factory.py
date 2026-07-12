"""Scaffold wiring helpers for MOD-RECO-027."""

from __future__ import annotations

from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .generator import ItemFeatureGenerator, build_default_item_feature_generator
from .in_memory_repository import (
    InMemoryConceptFeatureRuleRepository,
    InMemoryFeatureDefinitionRepository,
    InMemoryItemFeatureRepository,
    InMemoryItemValidation,
    InMemoryNormalizationRuleRepository,
    build_default_in_memory_repositories,
)


def build_scaffold_item_feature_generator(
    *,
    should_fail_upsert: bool = False,
) -> ItemFeatureGenerator:
    """Build generator backed by in-memory repositories (MVP scaffold)."""
    concept_rules, normalization_rules, feature_definitions, item_validation, item_feature_repo = (
        build_default_in_memory_repositories()
    )
    version_validation = InMemoryNormalizationRuleRepository()
    version_validation.semantic_config_version_id = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    return ItemFeatureGenerator(
        concept_feature_rules=concept_rules,
        normalization_rules=normalization_rules,
        feature_definitions=feature_definitions,
        item_validation=item_validation,
        item_feature_repository=InMemoryItemFeatureRepository(
            should_fail_on_upsert=should_fail_upsert,
        ),
        logger=ScaffoldRecoLogger(),
    )


__all__ = [
    "InMemoryConceptFeatureRuleRepository",
    "InMemoryFeatureDefinitionRepository",
    "InMemoryItemFeatureRepository",
    "InMemoryItemValidation",
    "InMemoryNormalizationRuleRepository",
    "ItemFeatureGenerator",
    "build_default_in_memory_repositories",
    "build_default_item_feature_generator",
    "build_scaffold_item_feature_generator",
]
