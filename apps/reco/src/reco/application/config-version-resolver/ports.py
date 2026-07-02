"""Repository ports for MOD-RECO-003 (IF-DB-RECO-001 read-only)."""

from __future__ import annotations

from typing import Protocol

from .models import (
    MatchingConfigRecord,
    ModelVersionRecord,
    RankingConfigRecord,
    ReasonTemplateRecord,
    SemanticConfigRecord,
    SemanticConfigVersionRecord,
)


class ConfigRepositoryPort(Protocol):
    """Read-only Config / Master access for version resolution."""

    def get_semantic_config_by_name(self, config_name: str) -> SemanticConfigRecord | None: ...

    def get_semantic_config_by_id(self, semantic_config_id: str) -> SemanticConfigRecord | None: ...

    def get_semantic_config_version_by_id(
        self, semantic_config_version_id: str
    ) -> SemanticConfigVersionRecord | None: ...

    def get_semantic_config_version_by_composite(
        self,
        *,
        config_name: str,
        version_label: str,
    ) -> SemanticConfigVersionRecord | None: ...

    def get_current_semantic_config_version(
        self, semantic_config_id: str
    ) -> SemanticConfigVersionRecord | None: ...

    def count_current_semantic_config_versions(
        self, semantic_config_id: str
    ) -> int: ...

    def get_model_version_by_id(self, model_version_id: str) -> ModelVersionRecord | None: ...

    def get_current_model_version(self, model_type: str) -> ModelVersionRecord | None: ...

    def get_current_ranking_config(self) -> RankingConfigRecord | None: ...

    def get_current_matching_config(self) -> MatchingConfigRecord | None: ...

    def count_feature_definitions(self, semantic_config_version_id: str) -> int: ...

    def count_active_reason_templates_by_type(self, template_type: str) -> int: ...
