"""Repository ports for MOD-RECO-005 (IF-DB-RECO-001 feature rule read)."""

from __future__ import annotations

from typing import Protocol

from .models import FeatureIntegrationWeights, FeatureVector


class FeatureRuleRepositoryPort(Protocol):
    """Read-only relationship_rule / occasion_rule / pair_rule / integration weights."""

    def get_relationship_features(
        self,
        relationship_code: str,
        semantic_config_version_id: str,
    ) -> FeatureVector | None: ...

    def get_occasion_features(
        self,
        occasion_code: str,
        semantic_config_version_id: str,
    ) -> FeatureVector | None: ...

    def get_pair_delta(
        self,
        relationship_code: str,
        occasion_code: str,
        semantic_config_version_id: str,
    ) -> FeatureVector | None:
        """Return None when pair_rule is undefined (caller applies all-zero delta)."""
        ...

    def get_integration_weights(
        self,
        semantic_config_version_id: str,
    ) -> FeatureIntegrationWeights: ...


class RunValidationPort(Protocol):
    """Read-only recommendation_run validation for external feature estimation."""

    def get_semantic_config_version_id(self, recommendation_run_id: str) -> str | None: ...
