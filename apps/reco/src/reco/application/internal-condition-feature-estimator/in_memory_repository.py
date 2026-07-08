"""In-memory concept feature rule repositories for MOD-RECO-006 unit tests and scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field

from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID

from .constants import (
    DEFAULT_FREE_TEXT_WEIGHT,
    POLARITY_NEGATIVE,
    POLARITY_POSITIVE,
)
from .models import ConceptFeatureRuleRecord, InternalFeatureIntegrationWeights
from .ports import ConceptFeatureRuleRepositoryPort, RunValidationPort

# Featureルール定義書 §10.3 の代表 Concept（稀疏 seed）
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
    ConceptFeatureRuleRecord("formal_refined", "intimacy", 0.05, POLARITY_NEGATIVE),
    ConceptFeatureRuleRecord(
        "formal_refined",
        "symbolic_identity",
        0.05,
        POLARITY_POSITIVE,
    ),
)

_PRESTIGIOUS_QUALITY_RULES: tuple[ConceptFeatureRuleRecord, ...] = (
    ConceptFeatureRuleRecord(
        "prestigious_quality",
        "formality",
        0.20,
        POLARITY_POSITIVE,
    ),
    ConceptFeatureRuleRecord("prestigious_quality", "safety", 0.10, POLARITY_POSITIVE),
    ConceptFeatureRuleRecord(
        "prestigious_quality",
        "brand_appropriateness",
        0.30,
        POLARITY_POSITIVE,
    ),
)

_EMOTIONAL_WARM_RULES: tuple[ConceptFeatureRuleRecord, ...] = (
    ConceptFeatureRuleRecord("emotional_warm", "safety", 0.05, POLARITY_POSITIVE),
    ConceptFeatureRuleRecord("emotional_warm", "emotion", 0.30, POLARITY_POSITIVE),
    ConceptFeatureRuleRecord("emotional_warm", "intimacy", 0.15, POLARITY_POSITIVE),
    ConceptFeatureRuleRecord(
        "emotional_warm",
        "symbolic_identity",
        0.05,
        POLARITY_POSITIVE,
    ),
    ConceptFeatureRuleRecord(
        "emotional_warm",
        "story_richness",
        0.05,
        POLARITY_POSITIVE,
    ),
)

_NOT_TOO_SAFE_RULES: tuple[ConceptFeatureRuleRecord, ...] = (
    ConceptFeatureRuleRecord("not_too_safe", "safety", 0.25, POLARITY_NEGATIVE),
    ConceptFeatureRuleRecord("not_too_safe", "novelty", 0.20, POLARITY_POSITIVE),
    ConceptFeatureRuleRecord(
        "not_too_safe",
        "symbolic_identity",
        0.05,
        POLARITY_POSITIVE,
    ),
    ConceptFeatureRuleRecord(
        "not_too_safe",
        "story_richness",
        0.05,
        POLARITY_POSITIVE,
    ),
)

_DEFAULT_RULES_BY_CONCEPT: dict[str, tuple[ConceptFeatureRuleRecord, ...]] = {
    "formal_refined": _FORMAL_REFINED_RULES,
    "prestigious_quality": _PRESTIGIOUS_QUALITY_RULES,
    "emotional_warm": _EMOTIONAL_WARM_RULES,
    "not_too_safe": _NOT_TOO_SAFE_RULES,
}


def build_default_concept_feature_rule_repository() -> InMemoryConceptFeatureRuleRepository:
    version_id = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    rules: dict[tuple[str, str], tuple[ConceptFeatureRuleRecord, ...]] = {
        (concept_code, version_id): rule_rows
        for concept_code, rule_rows in _DEFAULT_RULES_BY_CONCEPT.items()
    }
    return InMemoryConceptFeatureRuleRepository(
        semantic_config_version_id=version_id,
        rules_by_concept=rules,
    )


@dataclass
class InMemoryConceptFeatureRuleRepository:
    semantic_config_version_id: str = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    rules_by_concept: dict[tuple[str, str], tuple[ConceptFeatureRuleRecord, ...]] = field(
        default_factory=dict,
    )
    integration_weights: InternalFeatureIntegrationWeights = field(
        default_factory=lambda: InternalFeatureIntegrationWeights(
            preferred_weight=1.0,
            avoid_weight=1.0,
            free_text_weight=DEFAULT_FREE_TEXT_WEIGHT,
        ),
    )
    should_fail_on_lookup: bool = False

    def get_concept_feature_rules(
        self,
        concept_code: str,
        semantic_config_version_id: str,
    ) -> tuple[ConceptFeatureRuleRecord, ...]:
        if self.should_fail_on_lookup:
            raise RuntimeError("concept_feature_rule lookup failed")
        return self.rules_by_concept.get((concept_code, semantic_config_version_id), ())

    def get_integration_weights(
        self,
        semantic_config_version_id: str,
    ) -> InternalFeatureIntegrationWeights:
        if semantic_config_version_id != self.semantic_config_version_id:
            return InternalFeatureIntegrationWeights(
                preferred_weight=1.0,
                avoid_weight=1.0,
                free_text_weight=DEFAULT_FREE_TEXT_WEIGHT,
            )
        return self.integration_weights


@dataclass
class InMemoryRunValidation:
    """Tracks run_id -> semantic_config_version_id for estimation validation."""

    run_versions: dict[str, str] = field(default_factory=dict)

    def register_run(self, run_id: str, semantic_config_version_id: str) -> None:
        self.run_versions[run_id] = semantic_config_version_id

    def get_semantic_config_version_id(self, recommendation_run_id: str) -> str | None:
        return self.run_versions.get(recommendation_run_id)


def build_default_in_memory_repositories() -> tuple[
    ConceptFeatureRuleRepositoryPort,
    RunValidationPort,
]:
    return build_default_concept_feature_rule_repository(), InMemoryRunValidation()
