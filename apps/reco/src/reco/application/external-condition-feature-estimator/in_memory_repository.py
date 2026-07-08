"""In-memory feature rule repositories for MOD-RECO-005 unit tests and scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field

from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID

from .constants import DEFAULT_OCCASION_WEIGHT, DEFAULT_RELATIONSHIP_WEIGHT
from .models import FeatureIntegrationWeights
from .ports import FeatureRuleRepositoryPort, RunValidationPort

# Featureルール定義書 §6.2 / §8.2 / §9.3 の代表値（MVP scaffold）
_RELATIONSHIP_FEATURES: dict[str, dict[str, float]] = {
    "lover": {
        "formality": 0.35,
        "safety": 0.45,
        "brand_appropriateness": 0.55,
        "emotion": 0.85,
        "novelty": 0.65,
        "intimacy": 0.95,
        "symbolic_identity": 0.85,
        "story_richness": 0.75,
    },
    "boss": {
        "formality": 0.85,
        "safety": 0.85,
        "brand_appropriateness": 0.85,
        "emotion": 0.35,
        "novelty": 0.25,
        "intimacy": 0.20,
        "symbolic_identity": 0.35,
        "story_richness": 0.35,
    },
    "friend_casual": {
        "formality": 0.35,
        "safety": 0.70,
        "brand_appropriateness": 0.45,
        "emotion": 0.45,
        "novelty": 0.45,
        "intimacy": 0.45,
        "symbolic_identity": 0.45,
        "story_richness": 0.35,
    },
    "other": {
        "formality": 0.50,
        "safety": 0.60,
        "brand_appropriateness": 0.50,
        "emotion": 0.40,
        "novelty": 0.40,
        "intimacy": 0.40,
        "symbolic_identity": 0.40,
        "story_richness": 0.40,
    },
}

_OCCASION_FEATURES: dict[str, dict[str, float]] = {
    "birthday": {
        "formality": 0.40,
        "safety": 0.55,
        "brand_appropriateness": 0.50,
        "emotion": 0.75,
        "novelty": 0.65,
        "intimacy": 0.65,
        "symbolic_identity": 0.65,
        "story_richness": 0.60,
    },
    "thanks": {
        "formality": 0.55,
        "safety": 0.75,
        "brand_appropriateness": 0.65,
        "emotion": 0.70,
        "novelty": 0.35,
        "intimacy": 0.45,
        "symbolic_identity": 0.50,
        "story_richness": 0.45,
    },
    "other": {
        "formality": 0.50,
        "safety": 0.60,
        "brand_appropriateness": 0.50,
        "emotion": 0.50,
        "novelty": 0.40,
        "intimacy": 0.40,
        "symbolic_identity": 0.40,
        "story_richness": 0.40,
    },
}

_PAIR_DELTAS: dict[tuple[str, str], dict[str, float]] = {
    ("lover", "birthday"): {
        "formality": -0.05,
        "safety": -0.05,
        "brand_appropriateness": 0.00,
        "emotion": 0.10,
        "novelty": 0.10,
        "intimacy": 0.10,
        "symbolic_identity": 0.10,
        "story_richness": 0.10,
    },
    ("boss", "birthday"): {
        "formality": 0.15,
        "safety": 0.15,
        "brand_appropriateness": 0.15,
        "emotion": -0.10,
        "novelty": -0.10,
        "intimacy": -0.15,
        "symbolic_identity": -0.05,
        "story_richness": 0.00,
    },
    ("other", "other"): {
        "formality": 0.00,
        "safety": 0.00,
        "brand_appropriateness": 0.00,
        "emotion": 0.00,
        "novelty": 0.00,
        "intimacy": 0.00,
        "symbolic_identity": 0.00,
        "story_richness": 0.00,
    },
}


def build_default_feature_rule_repository() -> InMemoryFeatureRuleRepository:
    version_id = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    return InMemoryFeatureRuleRepository(
        semantic_config_version_id=version_id,
        relationship_features={
            (code, version_id): values for code, values in _RELATIONSHIP_FEATURES.items()
        },
        occasion_features={
            (code, version_id): values for code, values in _OCCASION_FEATURES.items()
        },
        pair_deltas={
            (rel, occ, version_id): values
            for (rel, occ), values in _PAIR_DELTAS.items()
        },
    )


@dataclass
class InMemoryFeatureRuleRepository:
    semantic_config_version_id: str = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    relationship_features: dict[tuple[str, str], dict[str, float]] = field(
        default_factory=dict,
    )
    occasion_features: dict[tuple[str, str], dict[str, float]] = field(default_factory=dict)
    pair_deltas: dict[tuple[str, str, str], dict[str, float]] = field(default_factory=dict)
    integration_weights: FeatureIntegrationWeights = field(
        default_factory=lambda: FeatureIntegrationWeights(
            relationship_weight=DEFAULT_RELATIONSHIP_WEIGHT,
            occasion_weight=DEFAULT_OCCASION_WEIGHT,
        ),
    )

    def get_relationship_features(
        self,
        relationship_code: str,
        semantic_config_version_id: str,
    ) -> dict[str, float] | None:
        return self.relationship_features.get((relationship_code, semantic_config_version_id))

    def get_occasion_features(
        self,
        occasion_code: str,
        semantic_config_version_id: str,
    ) -> dict[str, float] | None:
        return self.occasion_features.get((occasion_code, semantic_config_version_id))

    def get_pair_delta(
        self,
        relationship_code: str,
        occasion_code: str,
        semantic_config_version_id: str,
    ) -> dict[str, float] | None:
        return self.pair_deltas.get(
            (relationship_code, occasion_code, semantic_config_version_id),
        )

    def get_integration_weights(
        self,
        semantic_config_version_id: str,
    ) -> FeatureIntegrationWeights:
        if semantic_config_version_id != self.semantic_config_version_id:
            return FeatureIntegrationWeights(
                relationship_weight=DEFAULT_RELATIONSHIP_WEIGHT,
                occasion_weight=DEFAULT_OCCASION_WEIGHT,
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
    FeatureRuleRepositoryPort,
    RunValidationPort,
]:
    return build_default_feature_rule_repository(), InMemoryRunValidation()
