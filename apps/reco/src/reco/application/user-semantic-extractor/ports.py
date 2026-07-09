"""Repository ports for MOD-RECO-004 (IF-DB-RECO-003 / semantic catalog read)."""

from __future__ import annotations

from typing import Protocol

from .models import SemanticConceptRecord, SemanticRuleRecord, UserSemanticRecord


class SemanticCatalogPort(Protocol):
    """Read-only semantic_rule / semantic_concept access."""

    def list_active_concepts(
        self, semantic_config_version_id: str
    ) -> tuple[SemanticConceptRecord, ...]: ...

    def list_rules(self, semantic_config_version_id: str) -> tuple[SemanticRuleRecord, ...]: ...


class RunValidationPort(Protocol):
    """Read-only recommendation_run validation for extraction."""

    def get_semantic_config_version_id(self, recommendation_run_id: str) -> str | None: ...


class UserSemanticRepositoryPort(Protocol):
    """Persistence boundary for user_semantic (IF-DB-RECO-003)."""

    def exists_for_run(self, recommendation_run_id: str) -> bool: ...

    def insert(
        self,
        *,
        recommendation_run_id: str,
        semantic_config_version_id: str,
        extracted_semantic_json: dict[str, object],
    ) -> UserSemanticRecord: ...
