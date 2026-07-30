"""BATCH-010〜014 が利用する current version の DB 解決境界."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from batch.infrastructure.db import DbReader

DEFAULT_SEMANTIC_CONFIG_NAME = "mvp_semantic_config"
DEFAULT_NORMALIZATION_METHOD = "sigmoid"
EMBEDDING_MODEL_TYPE = "embedding"


class CurrentVersionResolveError(Exception):
    """current version を一意な UUID として解決できない場合の例外."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _require_single_uuid(
    rows: tuple[dict[str, object], ...],
    *,
    id_column: str,
    code: str,
    label: str,
) -> str:
    if len(rows) != 1:
        raise CurrentVersionResolveError(
            code,
            f"{label} current row count must be 1, got {len(rows)}",
        )
    raw = rows[0].get(id_column)
    try:
        return str(uuid.UUID(str(raw)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise CurrentVersionResolveError(
            code,
            f"{label} current {id_column} must be UUID",
        ) from exc


@dataclass(frozen=True)
class CurrentVersionResolver:
    """既存 DbReader の equality filter だけで current UUID を解決する."""

    db_reader: DbReader

    def resolve_semantic(
        self,
        *,
        config_name: str = DEFAULT_SEMANTIC_CONFIG_NAME,
    ) -> str:
        configs = self.db_reader.fetch_rows(
            "semantic_config",
            columns=("semantic_config_id",),
            equals=(("config_name", config_name), ("is_active", True)),
            limit=2,
        )
        semantic_config_id = _require_single_uuid(
            configs.rows,
            id_column="semantic_config_id",
            code="GRS-CFG-002",
            label=f"semantic config {config_name}",
        )
        versions = self.db_reader.fetch_rows(
            "semantic_config_version",
            columns=("semantic_config_version_id",),
            equals=(
                ("semantic_config_id", semantic_config_id),
                ("is_current", True),
            ),
            limit=2,
        )
        return _require_single_uuid(
            versions.rows,
            id_column="semantic_config_version_id",
            code="GRS-CFG-002",
            label=f"semantic config version {config_name}",
        )

    def resolve_normalization(
        self,
        *,
        semantic_config_version_id: str,
        normalization_method: str = DEFAULT_NORMALIZATION_METHOD,
    ) -> str:
        versions = self.db_reader.fetch_rows(
            "feature_normalization_version",
            columns=("feature_normalization_version_id",),
            equals=(
                ("normalization_method", normalization_method),
                ("is_current", True),
            ),
            limit=2,
        )
        version_id = _require_single_uuid(
            versions.rows,
            id_column="feature_normalization_version_id",
            code="GRS-CFG-001",
            label=f"feature normalization version {normalization_method}",
        )
        bindings = self.db_reader.fetch_rows(
            "normalization_rule",
            columns=("normalization_rule_id",),
            equals=(
                ("semantic_config_version_id", semantic_config_version_id),
                ("normalization_method", normalization_method),
                ("feature_normalization_version_id", version_id),
                ("is_active", True),
            ),
            limit=2,
        )
        _require_single_uuid(
            bindings.rows,
            id_column="normalization_rule_id",
            code="GRS-CFG-001",
            label=f"normalization binding {normalization_method}",
        )
        return version_id

    def resolve_embedding_model(self) -> str:
        versions = self.db_reader.fetch_rows(
            "model_version",
            columns=("model_version_id",),
            equals=(("model_type", EMBEDDING_MODEL_TYPE), ("is_current", True)),
            limit=2,
        )
        return _require_single_uuid(
            versions.rows,
            id_column="model_version_id",
            code="GRS-CFG-003",
            label="embedding model version",
        )
