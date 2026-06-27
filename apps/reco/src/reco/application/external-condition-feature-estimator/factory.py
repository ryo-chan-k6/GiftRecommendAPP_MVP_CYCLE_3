"""Scaffold wiring helpers for MOD-RECO-005."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .estimator import (
    ExternalConditionFeatureEstimator,
    build_default_external_condition_feature_estimator,
)
from .in_memory_repository import (
    InMemoryFeatureRuleRepository,
    InMemoryRunValidation,
    build_default_feature_rule_repository,
    build_default_in_memory_repositories,
)


def build_scaffold_external_condition_feature_estimator() -> ExternalConditionFeatureEstimator:
    """Build estimator backed by in-memory repositories (MVP scaffold)."""
    feature_rules = build_default_feature_rule_repository()
    run_validation = InMemoryRunValidation()
    return ExternalConditionFeatureEstimator(
        feature_rules=feature_rules,
        run_validation=run_validation,
        logger=ScaffoldRecoLogger(),
    )


__all__ = [
    "ExternalConditionFeatureEstimator",
    "InMemoryFeatureRuleRepository",
    "InMemoryRunValidation",
    "build_default_external_condition_feature_estimator",
    "build_default_feature_rule_repository",
    "build_default_in_memory_repositories",
    "build_scaffold_external_condition_feature_estimator",
]
