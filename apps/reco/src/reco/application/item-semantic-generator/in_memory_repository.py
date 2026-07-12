"""In-memory repositories for MOD-RECO-026 unit tests and scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID

from .models import ItemSemanticRecord, SemanticConceptRecord, SemanticRuleRecord
from .ports import (
    ItemSemanticRepositoryPort,
    ItemValidationPort,
    SemanticCatalogPort,
    SemanticConfigVersionPort,
)

DEFAULT_FORMAL_REFINED_CODE = "formal_refined"
DEFAULT_SAFE_CLASSIC_CODE = "safe_classic"
DEFAULT_PRESTIGIOUS_QUALITY_CODE = "prestigious_quality"


def build_default_semantic_catalog() -> InMemorySemanticCatalog:
    version_id = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    return InMemorySemanticCatalog(
        concepts=[
            SemanticConceptRecord(DEFAULT_FORMAL_REFINED_CODE, version_id),
            SemanticConceptRecord(DEFAULT_SAFE_CLASSIC_CODE, version_id),
            SemanticConceptRecord(DEFAULT_PRESTIGIOUS_QUALITY_CODE, version_id),
        ],
        rules=[
            SemanticRuleRecord(
                semantic_config_version_id=version_id,
                rule_type="phrase",
                match_value="上質な包装",
                concept_code=DEFAULT_FORMAL_REFINED_CODE,
                confidence=0.85,
                source_types=("item_description",),
            ),
            SemanticRuleRecord(
                semantic_config_version_id=version_id,
                rule_type="keyword",
                match_value="定番",
                concept_code=DEFAULT_SAFE_CLASSIC_CODE,
                confidence=0.72,
                source_types=("item_name", "item_description"),
            ),
            SemanticRuleRecord(
                semantic_config_version_id=version_id,
                rule_type="phrase",
                match_value="高級感",
                concept_code=DEFAULT_PRESTIGIOUS_QUALITY_CODE,
                confidence=0.88,
                source_types=("item_review", "item_description"),
            ),
        ],
    )


@dataclass
class InMemorySemanticCatalog:
    concepts: list[SemanticConceptRecord] = field(default_factory=list)
    rules: list[SemanticRuleRecord] = field(default_factory=list)

    def list_active_concepts(
        self, semantic_config_version_id: str
    ) -> tuple[SemanticConceptRecord, ...]:
        return tuple(
            concept
            for concept in self.concepts
            if concept.semantic_config_version_id == semantic_config_version_id
            and concept.is_active
        )

    def list_rules(self, semantic_config_version_id: str) -> tuple[SemanticRuleRecord, ...]:
        return tuple(
            rule
            for rule in self.rules
            if rule.semantic_config_version_id == semantic_config_version_id
        )


@dataclass
class InMemoryItemValidation:
    item_ids: set[str] = field(default_factory=set)

    def register_item(self, item_id: str) -> None:
        self.item_ids.add(item_id)

    def item_exists(self, item_id: str) -> bool:
        return item_id in self.item_ids


@dataclass
class InMemorySemanticConfigVersion:
    valid_version_ids: set[str] = field(default_factory=set)

    def register_version(self, semantic_config_version_id: str) -> None:
        self.valid_version_ids.add(semantic_config_version_id)

    def is_valid_version(self, semantic_config_version_id: str) -> bool:
        return semantic_config_version_id in self.valid_version_ids


@dataclass
class InMemoryItemSemanticRepository:
    rows: dict[tuple[str, str], ItemSemanticRecord] = field(default_factory=dict)
    should_fail_on_upsert: bool = False

    def find_by_item_and_version(
        self,
        *,
        item_id: str,
        semantic_config_version_id: str,
    ) -> ItemSemanticRecord | None:
        return self.rows.get((item_id, semantic_config_version_id))

    def upsert(
        self,
        *,
        item_id: str,
        semantic_config_version_id: str,
        semantic_json: dict[str, object],
        semantic_input_hash: str,
    ) -> ItemSemanticRecord:
        if self.should_fail_on_upsert:
            raise RuntimeError("item_semantic upsert failed")

        key = (item_id, semantic_config_version_id)
        existing = self.rows.get(key)
        record = ItemSemanticRecord(
            item_semantic_id=existing.item_semantic_id if existing else str(uuid4()),
            item_id=item_id,
            semantic_config_version_id=semantic_config_version_id,
            semantic_json=semantic_json,
            semantic_input_hash=semantic_input_hash,
        )
        self.rows[key] = record
        return record


def build_default_in_memory_repositories() -> tuple[
    SemanticCatalogPort,
    ItemValidationPort,
    SemanticConfigVersionPort,
    ItemSemanticRepositoryPort,
]:
    catalog = build_default_semantic_catalog()
    item_validation = InMemoryItemValidation()
    version_validation = InMemorySemanticConfigVersion()
    version_validation.register_version(DEFAULT_SEMANTIC_CONFIG_VERSION_ID)
    item_semantic_repo = InMemoryItemSemanticRepository()
    return catalog, item_validation, version_validation, item_semantic_repo
