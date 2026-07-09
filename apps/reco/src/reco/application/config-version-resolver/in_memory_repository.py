"""In-memory Config repository for unit tests and scaffold (no DB)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import (
    MatchingConfigRecord,
    ModelVersionRecord,
    RankingConfigRecord,
    ReasonTemplateRecord,
    SemanticConfigRecord,
    SemanticConfigVersionRecord,
)
from .ports import ConfigRepositoryPort

# Seed-aligned fixed IDs (supabase/seeds/masters/03_semantic_config.sql)
DEFAULT_SEMANTIC_CONFIG_ID = "a1111111-1111-4111-8111-111111111101"
DEFAULT_SEMANTIC_CONFIG_VERSION_ID = "a1111111-1111-4111-8111-111111111102"
DEFAULT_EMBEDDING_MODEL_VERSION_ID = "b1111111-1111-4111-8111-111111111101"
DEFAULT_LLM_MODEL_VERSION_ID = "b1111111-1111-4111-8111-111111111102"
DEFAULT_RANKING_MODEL_VERSION_ID = "b1111111-1111-4111-8111-111111111103"
DEFAULT_RANKING_CONFIG_ID = "c1111111-1111-4111-8111-111111111101"
DEFAULT_MATCHING_CONFIG_ID = "c1111111-1111-4111-8111-111111111102"

DEFAULT_MATCHING_PARAMETER_JSON: dict[str, object] = {
    "distance_method": "absolute_distance",
    "feature_match_method": "one_minus_distance",
    "social_feature_weights": {
        "formality": 0.333,
        "safety": 0.333,
        "brand_appropriateness": 0.333,
    },
    "symbolic_feature_weights": {
        "emotion": 0.200,
        "novelty": 0.200,
        "intimacy": 0.200,
        "symbolic_identity": 0.200,
        "story_richness": 0.200,
    },
    "context_score_formula": "lambda_ctx_weighted",
    "avoid_similarity_method": "mvp_default",
    "threshold_rule": {"strong_match": 0.80, "normal_match": 0.60},
}


def build_default_in_memory_repository() -> InMemoryConfigRepository:
    """MVP default catalog matching seed semantics."""
    return InMemoryConfigRepository(
        semantic_configs=[
            SemanticConfigRecord(
                semantic_config_id=DEFAULT_SEMANTIC_CONFIG_ID,
                config_name="mvp_semantic_config",
                is_active=True,
            ),
            SemanticConfigRecord(
                semantic_config_id="a1111111-1111-4111-8111-111111111199",
                config_name="treatment_semantic_config",
                is_active=True,
            ),
        ],
        semantic_config_versions=[
            SemanticConfigVersionRecord(
                semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
                semantic_config_id=DEFAULT_SEMANTIC_CONFIG_ID,
                version_label="v1.0.0",
                is_current=True,
            ),
            SemanticConfigVersionRecord(
                semantic_config_version_id="a1111111-1111-4111-8111-111111111199",
                semantic_config_id="a1111111-1111-4111-8111-111111111199",
                version_label="v1.0.0",
                is_current=True,
            ),
        ],
        model_versions=[
            ModelVersionRecord(
                model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION_ID,
                model_type="embedding",
                is_current=True,
            ),
            ModelVersionRecord(
                model_version_id=DEFAULT_LLM_MODEL_VERSION_ID,
                model_type="llm",
                is_current=True,
            ),
            ModelVersionRecord(
                model_version_id=DEFAULT_RANKING_MODEL_VERSION_ID,
                model_type="ranking",
                is_current=True,
            ),
        ],
        ranking_configs=[
            RankingConfigRecord(
                ranking_config_id=DEFAULT_RANKING_CONFIG_ID,
                config_name="mvp_ranking_config",
                is_current=True,
            ),
        ],
        matching_configs=[
            MatchingConfigRecord(
                matching_config_id=DEFAULT_MATCHING_CONFIG_ID,
                config_name="mvp_matching_config",
                is_current=True,
                parameter_json=DEFAULT_MATCHING_PARAMETER_JSON,
            ),
        ],
        reason_templates=[
            ReasonTemplateRecord("d1111111-1111-4111-8111-111111111101", "summary", True),
            ReasonTemplateRecord("d1111111-1111-4111-8111-111111111102", "detail", True),
            ReasonTemplateRecord("d1111111-1111-4111-8111-111111111103", "point", True),
            ReasonTemplateRecord("d1111111-1111-4111-8111-111111111104", "caution", True),
        ],
        feature_definition_counts={
            DEFAULT_SEMANTIC_CONFIG_VERSION_ID: 8,
            "a1111111-1111-4111-8111-111111111199": 8,
        },
    )


@dataclass
class InMemoryConfigRepository:
    """Read-only in-memory implementation of ConfigRepositoryPort."""

    semantic_configs: list[SemanticConfigRecord] = field(default_factory=list)
    semantic_config_versions: list[SemanticConfigVersionRecord] = field(
        default_factory=list
    )
    model_versions: list[ModelVersionRecord] = field(default_factory=list)
    ranking_configs: list[RankingConfigRecord] = field(default_factory=list)
    matching_configs: list[MatchingConfigRecord] = field(default_factory=list)
    reason_templates: list[ReasonTemplateRecord] = field(default_factory=list)
    feature_definition_counts: dict[str, int] = field(default_factory=dict)

    def get_semantic_config_by_name(self, config_name: str) -> SemanticConfigRecord | None:
        for record in self.semantic_configs:
            if record.config_name == config_name:
                return record
        return None

    def get_semantic_config_by_id(self, semantic_config_id: str) -> SemanticConfigRecord | None:
        for record in self.semantic_configs:
            if record.semantic_config_id == semantic_config_id:
                return record
        return None

    def get_semantic_config_version_by_id(
        self, semantic_config_version_id: str
    ) -> SemanticConfigVersionRecord | None:
        for record in self.semantic_config_versions:
            if record.semantic_config_version_id == semantic_config_version_id:
                return record
        return None

    def get_semantic_config_version_by_composite(
        self,
        *,
        config_name: str,
        version_label: str,
    ) -> SemanticConfigVersionRecord | None:
        config = self.get_semantic_config_by_name(config_name)
        if config is None:
            return None
        for record in self.semantic_config_versions:
            if (
                record.semantic_config_id == config.semantic_config_id
                and record.version_label == version_label
            ):
                return record
        return None

    def get_current_semantic_config_version(
        self, semantic_config_id: str
    ) -> SemanticConfigVersionRecord | None:
        current = [
            record
            for record in self.semantic_config_versions
            if record.semantic_config_id == semantic_config_id and record.is_current
        ]
        if len(current) != 1:
            return None
        return current[0]

    def count_current_semantic_config_versions(self, semantic_config_id: str) -> int:
        return sum(
            1
            for record in self.semantic_config_versions
            if record.semantic_config_id == semantic_config_id and record.is_current
        )

    def get_model_version_by_id(self, model_version_id: str) -> ModelVersionRecord | None:
        for record in self.model_versions:
            if record.model_version_id == model_version_id:
                return record
        return None

    def get_current_model_version(self, model_type: str) -> ModelVersionRecord | None:
        current = [
            record
            for record in self.model_versions
            if record.model_type == model_type and record.is_current
        ]
        if len(current) != 1:
            return None
        return current[0]

    def get_current_ranking_config(self) -> RankingConfigRecord | None:
        current = [record for record in self.ranking_configs if record.is_current]
        if len(current) != 1:
            return None
        return current[0]

    def get_current_matching_config(self) -> MatchingConfigRecord | None:
        current = [record for record in self.matching_configs if record.is_current]
        if len(current) != 1:
            return None
        return current[0]

    def count_feature_definitions(self, semantic_config_version_id: str) -> int:
        return self.feature_definition_counts.get(semantic_config_version_id, 0)

    def count_active_reason_templates_by_type(self, template_type: str) -> int:
        return sum(
            1
            for record in self.reason_templates
            if record.template_type == template_type and record.is_active
        )
