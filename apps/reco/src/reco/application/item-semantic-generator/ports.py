"""Ports for MOD-RECO-026 Item Semantic Generator."""

from __future__ import annotations

from typing import Protocol

from .models import (
    ItemSemanticGenerationContext,
    ItemSemanticGenerationResult,
    ItemSemanticRecord,
    SemanticConceptRecord,
    SemanticRuleRecord,
)


class ItemSemanticGeneratorPort(Protocol):
    """Batch-facing port contract (§8.3.5)."""

    module_id: str

    def generate_item_semantic(
        self,
        context: ItemSemanticGenerationContext,
    ) -> ItemSemanticGenerationResult: ...


class SemanticCatalogPort(Protocol):
    """Read-only semantic_rule / semantic_concept access."""

    def list_active_concepts(
        self, semantic_config_version_id: str
    ) -> tuple[SemanticConceptRecord, ...]: ...

    def list_rules(self, semantic_config_version_id: str) -> tuple[SemanticRuleRecord, ...]: ...


class ItemValidationPort(Protocol):
    """Read-only item master validation."""

    def item_exists(self, item_id: str) -> bool: ...


class SemanticConfigVersionPort(Protocol):
    """Read-only semantic_config_version validation."""

    def is_valid_version(self, semantic_config_version_id: str) -> bool: ...


class ItemSemanticRepositoryPort(Protocol):
    """Persistence boundary for item_semantic."""

    def find_by_item_and_version(
        self,
        *,
        item_id: str,
        semantic_config_version_id: str,
    ) -> ItemSemanticRecord | None: ...

    def upsert(
        self,
        *,
        item_id: str,
        semantic_config_version_id: str,
        semantic_json: dict[str, object],
        semantic_input_hash: str,
    ) -> ItemSemanticRecord: ...
