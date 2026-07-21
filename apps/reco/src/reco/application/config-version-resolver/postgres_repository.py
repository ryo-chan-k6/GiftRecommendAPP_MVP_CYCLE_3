"""PostgreSQL ConfigRepositoryPort for production config version resolution."""

from __future__ import annotations

from dataclasses import dataclass

from reco.infrastructure.db.session import DatabaseSession

from .in_memory_repository import build_default_in_memory_repository
from .models import (
    MatchingConfigRecord,
    ModelVersionRecord,
    RankingConfigRecord,
    SemanticConfigRecord,
    SemanticConfigVersionRecord,
)
from .ports import ConfigRepositoryPort


def _as_dict(parameter_json: object) -> dict[str, object]:
    if isinstance(parameter_json, dict):
        return dict(parameter_json)
    return {}


@dataclass
class PostgresConfigRepository:
    """Read-only Config / Master access backed by PostgreSQL ``is_current`` rows."""

    session: DatabaseSession

    def get_semantic_config_by_name(self, config_name: str) -> SemanticConfigRecord | None:
        row = self.session.query_one(
            """
            SELECT semantic_config_id, config_name, is_active
            FROM semantic_config
            WHERE config_name = %s
            LIMIT 1
            """,
            (config_name,),
        )
        if row is None:
            return None
        return SemanticConfigRecord(
            semantic_config_id=str(row["semantic_config_id"]),
            config_name=str(row["config_name"]),
            is_active=bool(row["is_active"]),
        )

    def get_semantic_config_by_id(self, semantic_config_id: str) -> SemanticConfigRecord | None:
        row = self.session.query_one(
            """
            SELECT semantic_config_id, config_name, is_active
            FROM semantic_config
            WHERE semantic_config_id = %s
            LIMIT 1
            """,
            (semantic_config_id,),
        )
        if row is None:
            return None
        return SemanticConfigRecord(
            semantic_config_id=str(row["semantic_config_id"]),
            config_name=str(row["config_name"]),
            is_active=bool(row["is_active"]),
        )

    def get_semantic_config_version_by_id(
        self, semantic_config_version_id: str
    ) -> SemanticConfigVersionRecord | None:
        row = self.session.query_one(
            """
            SELECT
              semantic_config_version_id,
              semantic_config_id,
              version_label,
              is_current
            FROM semantic_config_version
            WHERE semantic_config_version_id = %s
            LIMIT 1
            """,
            (semantic_config_version_id,),
        )
        if row is None:
            return None
        return SemanticConfigVersionRecord(
            semantic_config_version_id=str(row["semantic_config_version_id"]),
            semantic_config_id=str(row["semantic_config_id"]),
            version_label=str(row["version_label"]),
            is_current=bool(row["is_current"]),
        )

    def get_semantic_config_version_by_composite(
        self,
        *,
        config_name: str,
        version_label: str,
    ) -> SemanticConfigVersionRecord | None:
        row = self.session.query_one(
            """
            SELECT
              v.semantic_config_version_id,
              v.semantic_config_id,
              v.version_label,
              v.is_current
            FROM semantic_config_version v
            INNER JOIN semantic_config c
              ON c.semantic_config_id = v.semantic_config_id
            WHERE c.config_name = %s
              AND v.version_label = %s
            LIMIT 1
            """,
            (config_name, version_label),
        )
        if row is None:
            return None
        return SemanticConfigVersionRecord(
            semantic_config_version_id=str(row["semantic_config_version_id"]),
            semantic_config_id=str(row["semantic_config_id"]),
            version_label=str(row["version_label"]),
            is_current=bool(row["is_current"]),
        )

    def get_current_semantic_config_version(
        self, semantic_config_id: str
    ) -> SemanticConfigVersionRecord | None:
        rows = self.session.query(
            """
            SELECT
              semantic_config_version_id,
              semantic_config_id,
              version_label,
              is_current
            FROM semantic_config_version
            WHERE semantic_config_id = %s
              AND is_current = true
            """,
            (semantic_config_id,),
        )
        if len(rows) != 1:
            return None
        row = rows[0]
        return SemanticConfigVersionRecord(
            semantic_config_version_id=str(row["semantic_config_version_id"]),
            semantic_config_id=str(row["semantic_config_id"]),
            version_label=str(row["version_label"]),
            is_current=bool(row["is_current"]),
        )

    def count_current_semantic_config_versions(self, semantic_config_id: str) -> int:
        row = self.session.query_one(
            """
            SELECT COUNT(*)::int AS count
            FROM semantic_config_version
            WHERE semantic_config_id = %s
              AND is_current = true
            """,
            (semantic_config_id,),
        )
        if row is None:
            return 0
        return int(row["count"])

    def get_model_version_by_id(self, model_version_id: str) -> ModelVersionRecord | None:
        row = self.session.query_one(
            """
            SELECT model_version_id, model_type, is_current
            FROM model_version
            WHERE model_version_id = %s
            LIMIT 1
            """,
            (model_version_id,),
        )
        if row is None:
            return None
        return ModelVersionRecord(
            model_version_id=str(row["model_version_id"]),
            model_type=str(row["model_type"]),
            is_current=bool(row["is_current"]),
        )

    def get_current_model_version(self, model_type: str) -> ModelVersionRecord | None:
        rows = self.session.query(
            """
            SELECT model_version_id, model_type, is_current
            FROM model_version
            WHERE model_type = %s
              AND is_current = true
            """,
            (model_type,),
        )
        if len(rows) != 1:
            return None
        row = rows[0]
        return ModelVersionRecord(
            model_version_id=str(row["model_version_id"]),
            model_type=str(row["model_type"]),
            is_current=bool(row["is_current"]),
        )

    def get_current_ranking_config(self) -> RankingConfigRecord | None:
        rows = self.session.query(
            """
            SELECT ranking_config_id, config_name, is_current
            FROM ranking_config
            WHERE is_current = true
            """
        )
        if len(rows) != 1:
            return None
        row = rows[0]
        return RankingConfigRecord(
            ranking_config_id=str(row["ranking_config_id"]),
            config_name=str(row["config_name"]),
            is_current=bool(row["is_current"]),
        )

    def get_current_matching_config(self) -> MatchingConfigRecord | None:
        rows = self.session.query(
            """
            SELECT matching_config_id, config_name, is_current, parameter_json
            FROM matching_config
            WHERE is_current = true
            """
        )
        if len(rows) != 1:
            return None
        row = rows[0]
        return MatchingConfigRecord(
            matching_config_id=str(row["matching_config_id"]),
            config_name=str(row["config_name"]),
            is_current=bool(row["is_current"]),
            parameter_json=_as_dict(row["parameter_json"]),
        )

    def count_feature_definitions(self, semantic_config_version_id: str) -> int:
        row = self.session.query_one(
            """
            SELECT COUNT(*)::int AS count
            FROM feature_definition
            WHERE semantic_config_version_id = %s
              AND is_active = true
            """,
            (semantic_config_version_id,),
        )
        if row is None:
            return 0
        return int(row["count"])

    def count_active_reason_templates_by_type(self, template_type: str) -> int:
        row = self.session.query_one(
            """
            SELECT COUNT(*)::int AS count
            FROM reason_template
            WHERE template_type = %s
              AND is_active = true
            """,
            (template_type,),
        )
        if row is None:
            return 0
        return int(row["count"])


@dataclass
class ProductionConfigRepository:
    """Postgres version catalog + reason_template InMemory fallback（master seed 未整備時）。"""

    postgres: PostgresConfigRepository
    reason_template_fallback: ConfigRepositoryPort

    def get_semantic_config_by_name(self, config_name: str) -> SemanticConfigRecord | None:
        return self.postgres.get_semantic_config_by_name(config_name)

    def get_semantic_config_by_id(self, semantic_config_id: str) -> SemanticConfigRecord | None:
        return self.postgres.get_semantic_config_by_id(semantic_config_id)

    def get_semantic_config_version_by_id(
        self, semantic_config_version_id: str
    ) -> SemanticConfigVersionRecord | None:
        return self.postgres.get_semantic_config_version_by_id(semantic_config_version_id)

    def get_semantic_config_version_by_composite(
        self,
        *,
        config_name: str,
        version_label: str,
    ) -> SemanticConfigVersionRecord | None:
        return self.postgres.get_semantic_config_version_by_composite(
            config_name=config_name,
            version_label=version_label,
        )

    def get_current_semantic_config_version(
        self, semantic_config_id: str
    ) -> SemanticConfigVersionRecord | None:
        return self.postgres.get_current_semantic_config_version(semantic_config_id)

    def count_current_semantic_config_versions(self, semantic_config_id: str) -> int:
        return self.postgres.count_current_semantic_config_versions(semantic_config_id)

    def get_model_version_by_id(self, model_version_id: str) -> ModelVersionRecord | None:
        return self.postgres.get_model_version_by_id(model_version_id)

    def get_current_model_version(self, model_type: str) -> ModelVersionRecord | None:
        return self.postgres.get_current_model_version(model_type)

    def get_current_ranking_config(self) -> RankingConfigRecord | None:
        return self.postgres.get_current_ranking_config()

    def get_current_matching_config(self) -> MatchingConfigRecord | None:
        return self.postgres.get_current_matching_config()

    def count_feature_definitions(self, semantic_config_version_id: str) -> int:
        return self.postgres.count_feature_definitions(semantic_config_version_id)

    def count_active_reason_templates_by_type(self, template_type: str) -> int:
        count = self.postgres.count_active_reason_templates_by_type(template_type)
        if count >= 1:
            return count
        return self.reason_template_fallback.count_active_reason_templates_by_type(
            template_type
        )


def build_production_config_repository(session: DatabaseSession) -> ProductionConfigRepository:
    """Build production config repository with reason_template catalog fallback."""

    return ProductionConfigRepository(
        postgres=PostgresConfigRepository(session=session),
        reason_template_fallback=build_default_in_memory_repository(),
    )
