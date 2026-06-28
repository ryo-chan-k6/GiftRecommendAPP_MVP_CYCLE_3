"""Scaffold wiring helpers for MOD-RECO-006."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .estimator import (
    InternalConditionFeatureEstimator,
    build_default_internal_condition_feature_estimator,
)
from .in_memory_repository import (
    InMemoryConceptFeatureRuleRepository,
    InMemoryRunValidation,
    build_default_concept_feature_rule_repository,
    build_default_in_memory_repositories,
)


def build_scaffold_internal_condition_feature_estimator() -> InternalConditionFeatureEstimator:
    """Build estimator backed by in-memory repositories (MVP scaffold)."""
    concept_feature_rules = build_default_concept_feature_rule_repository()
    run_validation = InMemoryRunValidation()
    return InternalConditionFeatureEstimator(
        concept_feature_rules=concept_feature_rules,
        run_validation=run_validation,
        logger=ScaffoldRecoLogger(),
    )


__all__ = [
    "InternalConditionFeatureEstimator",
    "InMemoryConceptFeatureRuleRepository",
    "InMemoryRunValidation",
    "build_default_concept_feature_rule_repository",
    "build_default_in_memory_repositories",
    "build_default_internal_condition_feature_estimator",
    "build_scaffold_internal_condition_feature_estimator",
]
