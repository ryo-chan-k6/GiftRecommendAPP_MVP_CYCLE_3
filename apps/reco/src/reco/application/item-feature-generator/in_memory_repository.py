"""In-memory repositories for MOD-RECO-027 unit tests and scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES

from .constants import (
    DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
    POLARITY_NEGATIVE,
    POLARITY_POSITIVE,
)
from .models import (
    ConceptFeatureRuleRecord,
    ItemFeatureRecord,
    ItemFeatureUpsertRow,
    NormalizationBinding,
)
from .ports import (
    ConceptFeatureRuleRepositoryPort,
    FeatureDefinitionRepositoryPort,
    ItemFeatureRepositoryPort,
    ItemValidationPort,
    NormalizationRuleRepositoryPort,
)

_FORMAL_REFINED_RULES: tuple[ConceptFeatureRuleRecord, ...] = (
    ConceptFeatureRuleRecord("formal_refined", "formality", 0.25, POLARITY_POSITIVE),
    ConceptFeatureRuleRecord("formal_refined", "safety", 0.05, POLARITY_POSITIVE),
    ConceptFeatureRuleRecord(
        "formal_refined",
        "brand_appropriateness",
        0.20,
        POLARITY_POSITIVE,
    ),
    ConceptFeatureRuleRecord("formal_refined", "novelty", 0.05, POLARITY_NEGATIVE),
)

_SAFE_CLASSIC_RULES: tuple[ConceptFeatureRuleRecord, ...] = (
    ConceptFeatureRuleRecord("safe_classic", "safety", 0.15, POLARITY_POSITIVE),
    ConceptFeatureRuleRecord("safe_classic", "formality", 0.10, POLARITY_POSITIVE),
)


def build_default_concept_feature_rules() -> tuple[ConceptFeatureRuleRecord, ...]:
    return _FORMAL_REFINED_RULES + _SAFE_CLASSIC_RULES


def build_default_normalization_binding() -> NormalizationBinding:
    return NormalizationBinding(
        feature_normalization_version_id=DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
    )


@dataclass
class InMemoryConceptFeatureRuleRepository:
    semantic_config_version_id: str = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    rules: tuple[ConceptFeatureRuleRecord, ...] = field(
        default_factory=build_default_concept_feature_rules,
    )
    should_fail_on_lookup: bool = False

    def list_active_rules(
        self,
        semantic_config_version_id: str,
    ) -> tuple[ConceptFeatureRuleRecord, ...]:
        if self.should_fail_on_lookup:
            raise RuntimeError("concept_feature_rule lookup failed")
        if semantic_config_version_id != self.semantic_config_version_id:
            return ()
        return tuple(rule for rule in self.rules if rule.is_active)


@dataclass
class InMemoryNormalizationRuleRepository:
    semantic_config_version_id: str = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    binding: NormalizationBinding | None = field(
        default_factory=build_default_normalization_binding,
    )
    should_fail_on_lookup: bool = False

    def get_active_normalization_binding(
        self,
        semantic_config_version_id: str,
    ) -> NormalizationBinding | None:
        if self.should_fail_on_lookup:
            raise RuntimeError("normalization_rule lookup failed")
        if semantic_config_version_id != self.semantic_config_version_id:
            return None
        return self.binding


@dataclass
class InMemoryFeatureDefinitionRepository:
    semantic_config_version_id: str = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    feature_codes: tuple[str, ...] = MVP_FEATURE_CODES

    def list_active_feature_codes(
        self,
        semantic_config_version_id: str,
    ) -> tuple[str, ...]:
        if semantic_config_version_id != self.semantic_config_version_id:
            return ()
        return self.feature_codes


@dataclass
class InMemoryItemValidation:
    item_ids: set[str] = field(default_factory=set)

    def register_item(self, item_id: str) -> None:
        self.item_ids.add(item_id)

    def item_exists(self, item_id: str) -> bool:
        return item_id in self.item_ids


@dataclass
class InMemoryItemFeatureRepository:
    rows: dict[tuple[str, str, str, str, str], ItemFeatureRecord] = field(
        default_factory=dict,
    )
    should_fail_on_upsert: bool = False

    def find_by_idempotent_key(
        self,
        *,
        item_id: str,
        semantic_config_version_id: str,
        feature_input_hash: str,
        feature_normalization_version_id: str,
    ) -> tuple[ItemFeatureRecord, ...]:
        matched = [
            row
            for key, row in self.rows.items()
            if key[0] == item_id
            and key[1] == semantic_config_version_id
            and key[3] == feature_input_hash
            and key[4] == feature_normalization_version_id
        ]
        return tuple(sorted(matched, key=lambda row: row.feature_code))

    def upsert(
        self,
        rows: tuple[ItemFeatureUpsertRow, ...],
    ) -> tuple[ItemFeatureRecord, ...]:
        if self.should_fail_on_upsert:
            raise RuntimeError("item_feature upsert failed")

        persisted: list[ItemFeatureRecord] = []
        for row in rows:
            key = (
                row.item_id,
                row.semantic_config_version_id,
                row.feature_code,
                row.feature_input_hash,
                row.feature_normalization_version_id,
            )
            existing = self.rows.get(key)
            record = ItemFeatureRecord(
                item_feature_id=existing.item_feature_id if existing else str(uuid4()),
                item_id=row.item_id,
                semantic_config_version_id=row.semantic_config_version_id,
                feature_code=row.feature_code,
                feature_input_hash=row.feature_input_hash,
                feature_normalization_version_id=row.feature_normalization_version_id,
                raw_feature_value=row.raw_feature_value,
                normalized_feature_value=None,
            )
            self.rows[key] = record
            persisted.append(record)
        return tuple(persisted)


def build_default_in_memory_repositories() -> tuple[
    ConceptFeatureRuleRepositoryPort,
    NormalizationRuleRepositoryPort,
    FeatureDefinitionRepositoryPort,
    ItemValidationPort,
    ItemFeatureRepositoryPort,
]:
    return (
        InMemoryConceptFeatureRuleRepository(),
        InMemoryNormalizationRuleRepository(),
        InMemoryFeatureDefinitionRepository(),
        InMemoryItemValidation(),
        InMemoryItemFeatureRepository(),
    )
