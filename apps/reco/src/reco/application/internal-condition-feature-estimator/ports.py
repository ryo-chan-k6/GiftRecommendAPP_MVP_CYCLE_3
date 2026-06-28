"""Repository ports for MOD-RECO-006 (IF-DB-RECO-001 concept_feature_rule read)."""

from __future__ import annotations

from typing import Protocol

from .models import ConceptFeatureRuleRecord, InternalFeatureIntegrationWeights


class ConceptFeatureRuleRepositoryPort(Protocol):
    """Read-only concept_feature_rule / feature_integration_rule access."""

    def get_concept_feature_rules(
        self,
        concept_code: str,
        semantic_config_version_id: str,
    ) -> tuple[ConceptFeatureRuleRecord, ...]: ...

    def get_integration_weights(
        self,
        semantic_config_version_id: str,
    ) -> InternalFeatureIntegrationWeights: ...


class RunValidationPort(Protocol):
    """Read-only recommendation_run validation for internal feature estimation."""

    def get_semantic_config_version_id(self, recommendation_run_id: str) -> str | None: ...
