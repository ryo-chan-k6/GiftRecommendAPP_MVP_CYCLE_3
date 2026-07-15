"""PostgreSQL ItemFeature + FeatureNormalization for MOD-RECO-014."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from reco.infrastructure.db.application_bootstrap import _load_application_module
from reco.infrastructure.db.session import DatabaseSession

_load_application_module(
    "reco.application.user_feature_generator",
    "user-feature-generator",
    "models",
)
from reco.application.user_feature_generator.models import (  # noqa: E402
    FeatureNormalizationParameters,
)

_FETCH_FEATURES_SQL_PREFIX = """
SELECT
  item_id::text AS item_id,
  feature_code,
  normalized_feature_value
FROM item_feature
WHERE semantic_config_version_id = %s
  AND item_id IN (
"""

_FETCH_NORM_SQL = """
SELECT
  normalization_method,
  parameter_json
FROM feature_normalization_version
WHERE feature_normalization_version_id = %s
LIMIT 1
"""


@dataclass
class PostgresItemFeatureRepository:
    """IF-DB-RECO-005 Postgres implementation for Feature Matcher."""

    session: DatabaseSession

    def fetch_item_features(
        self,
        item_ids: tuple[str, ...],
        semantic_config_version_id: str,
    ) -> dict[str, dict[str, float]]:
        if not item_ids:
            return {}
        placeholders = ", ".join(["%s"] * len(item_ids))
        sql = _FETCH_FEATURES_SQL_PREFIX + placeholders + ")"
        rows = self.session.query(
            sql,
            (semantic_config_version_id, *item_ids),
        )
        result: dict[str, dict[str, float]] = {}
        for row in rows:
            item_id = str(row["item_id"])
            features = result.setdefault(item_id, {})
            features[str(row["feature_code"])] = float(row["normalized_feature_value"])
        return result


@dataclass
class PostgresFeatureNormalizationRepository:
    """feature_normalization_version lookup for Feature Matcher."""

    session: DatabaseSession

    def get_parameters(
        self,
        feature_normalization_version_id: str,
    ) -> FeatureNormalizationParameters | None:
        row = self.session.query_one(
            _FETCH_NORM_SQL,
            (feature_normalization_version_id,),
        )
        if row is None:
            return None
        params = row["parameter_json"]
        if not isinstance(params, dict):
            raise TypeError(
                f"parameter_json must be object, got {type(params)!r}",
            )
        return FeatureNormalizationParameters(
            center_feature=float(params["center_feature"]),
            k_feature=float(params["k_feature"]),
            normalization_method=str(row["normalization_method"]),
        )
