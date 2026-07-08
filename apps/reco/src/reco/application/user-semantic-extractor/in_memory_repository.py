"""In-memory repositories for MOD-RECO-004 unit tests and scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID

from .models import SemanticConceptRecord, SemanticRuleRecord, UserSemanticRecord
from .ports import RunValidationPort, SemanticCatalogPort, UserSemanticRepositoryPort

DEFAULT_FORMAL_REFINED_CODE = "formal_refined"
DEFAULT_TOO_CASUAL_CODE = "too_casual"
DEFAULT_WARM_HEARTFELT_CODE = "warm_heartfelt"


def build_default_semantic_catalog() -> InMemorySemanticCatalog:
    version_id = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    return InMemorySemanticCatalog(
        concepts=[
            SemanticConceptRecord(DEFAULT_FORMAL_REFINED_CODE, version_id),
            SemanticConceptRecord(DEFAULT_TOO_CASUAL_CODE, version_id),
            SemanticConceptRecord(DEFAULT_WARM_HEARTFELT_CODE, version_id),
            SemanticConceptRecord("alcohol_ng", version_id),
        ],
        rules=[
            SemanticRuleRecord(
                semantic_config_version_id=version_id,
                rule_type="phrase",
                match_value="上品",
                concept_code=DEFAULT_FORMAL_REFINED_CODE,
                confidence=0.88,
                source_types=("preferred_condition",),
                input_intent="prefer",
            ),
            SemanticRuleRecord(
                semantic_config_version_id=version_id,
                rule_type="keyword",
                match_value="カジュアル",
                concept_code=DEFAULT_TOO_CASUAL_CODE,
                confidence=0.75,
                source_types=("non_preferred_condition",),
                input_intent="avoid",
            ),
            SemanticRuleRecord(
                semantic_config_version_id=version_id,
                rule_type="keyword",
                match_value="温かみ",
                concept_code=DEFAULT_WARM_HEARTFELT_CODE,
                confidence=0.82,
                source_types=("free_text", "preferred_condition"),
                input_intent="prefer",
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
class InMemoryRunValidation:
    """Tracks run_id -> semantic_config_version_id for extraction validation."""

    run_versions: dict[str, str] = field(default_factory=dict)

    def register_run(self, run_id: str, semantic_config_version_id: str) -> None:
        self.run_versions[run_id] = semantic_config_version_id

    def get_semantic_config_version_id(self, recommendation_run_id: str) -> str | None:
        return self.run_versions.get(recommendation_run_id)


@dataclass
class InMemoryUserSemanticRepository:
    rows: dict[str, UserSemanticRecord] = field(default_factory=dict)
    should_fail_on_insert: bool = False

    def exists_for_run(self, recommendation_run_id: str) -> bool:
        return recommendation_run_id in self.rows

    def insert(
        self,
        *,
        recommendation_run_id: str,
        semantic_config_version_id: str,
        extracted_semantic_json: dict[str, object],
    ) -> UserSemanticRecord:
        if self.should_fail_on_insert:
            raise RuntimeError("user_semantic insert failed")

        if recommendation_run_id in self.rows:
            raise RuntimeError("duplicate user_semantic row")

        record = UserSemanticRecord(
            user_semantic_id=str(uuid4()),
            recommendation_run_id=recommendation_run_id,
            semantic_config_version_id=semantic_config_version_id,
            extracted_semantic_json=extracted_semantic_json,
        )
        self.rows[recommendation_run_id] = record
        return record


def build_default_in_memory_repositories() -> tuple[
    SemanticCatalogPort,
    RunValidationPort,
    UserSemanticRepositoryPort,
]:
    catalog = build_default_semantic_catalog()
    run_validation = InMemoryRunValidation()
    user_semantic_repo = InMemoryUserSemanticRepository()
    return catalog, run_validation, user_semantic_repo
