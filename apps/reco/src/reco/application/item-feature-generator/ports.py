"""Ports for MOD-RECO-027 Item Feature Generator."""

from __future__ import annotations

from typing import Protocol

from .models import (
    ConceptFeatureRuleRecord,
    ItemFeatureGenerationContext,
    ItemFeatureGenerationResult,
    ItemFeatureRecord,
    ItemFeatureUpsertRow,
    NormalizationBinding,
)


class ItemFeatureGeneratorPort(Protocol):
    """Batch-facing port contract (§8.3.5)."""

    module_id: str

    def generate_item_features(
        self,
        context: ItemFeatureGenerationContext,
    ) -> ItemFeatureGenerationResult: ...


class ItemValidationPort(Protocol):
    """Read-only item master validation."""

    def item_exists(self, item_id: str) -> bool: ...


class ConceptFeatureRuleRepositoryPort(Protocol):
    """Read-only concept_feature_rule access."""

    def list_active_rules(
        self,
        semantic_config_version_id: str,
    ) -> tuple[ConceptFeatureRuleRecord, ...]: ...


class NormalizationRuleRepositoryPort(Protocol):
    """Read-only normalization_rule / feature_normalization_version access."""

    def get_active_normalization_binding(
        self,
        semantic_config_version_id: str,
    ) -> NormalizationBinding | None: ...


class FeatureDefinitionRepositoryPort(Protocol):
    """Read-only feature_definition validation."""

    def list_active_feature_codes(
        self,
        semantic_config_version_id: str,
    ) -> tuple[str, ...]: ...


class ItemFeatureRepositoryPort(Protocol):
    """Persistence boundary for item_feature."""

    def find_by_idempotent_key(
        self,
        *,
        item_id: str,
        semantic_config_version_id: str,
        feature_input_hash: str,
        feature_normalization_version_id: str,
    ) -> tuple[ItemFeatureRecord, ...]: ...

    def upsert(
        self,
        rows: tuple[ItemFeatureUpsertRow, ...],
    ) -> tuple[ItemFeatureRecord, ...]: ...
