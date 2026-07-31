"""PostgreSQL FeatureRuleRepository for MOD-RECO-005."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from reco.domain.gift_meaning.features import MVP_FEATURE_CODES
from reco.infrastructure.db.application_bootstrap import _load_application_module
from reco.infrastructure.db.session import DatabaseSession

_APPLICATION_IMPORT_ROOT = "reco.application.external_condition_feature_estimator"
_APPLICATION_PACKAGE_DIR = "external-condition-feature-estimator"

_load_application_module(
    _APPLICATION_IMPORT_ROOT,
    _APPLICATION_PACKAGE_DIR,
    "models",
)
_load_application_module(
    _APPLICATION_IMPORT_ROOT,
    _APPLICATION_PACKAGE_DIR,
    "constants",
)
from reco.application.external_condition_feature_estimator.constants import (  # noqa: E402
    DEFAULT_OCCASION_WEIGHT,
    DEFAULT_RELATIONSHIP_WEIGHT,
)
from reco.application.external_condition_feature_estimator.models import (  # noqa: E402
    FeatureIntegrationWeights,
    FeatureVector,
)

_RELATIONSHIP_FEATURE_SQL = """
SELECT feature_code, feature_base_value
FROM relationship_rule
WHERE semantic_config_version_id = %s
  AND relationship_code = %s
  AND is_active = true
"""

_OCCASION_FEATURE_SQL = """
SELECT feature_code, feature_base_value
FROM occasion_rule
WHERE semantic_config_version_id = %s
  AND occasion_code = %s
  AND is_active = true
"""

_PAIR_ID_SQL = """
SELECT pair_id
FROM pair_master
WHERE relationship_code = %s
  AND occasion_code = %s
  AND is_active = true
LIMIT 1
"""

_PAIR_DELTA_SQL = """
SELECT feature_code, feature_delta
FROM pair_rule
WHERE semantic_config_version_id = %s
  AND pair_id = %s
  AND is_active = true
"""

_INTEGRATION_WEIGHTS_SQL = """
SELECT feature_code, input_source, weight
FROM feature_integration_rule
WHERE semantic_config_version_id = %s
  AND input_source IN ('relationship_feature', 'occasion_feature')
  AND is_active = true
"""

_MVP_FEATURE_CODE_SET = frozenset(MVP_FEATURE_CODES)


def _rows_to_feature_vector(
    rows: list[dict[str, Any]],
    *,
    value_column: str,
) -> FeatureVector | None:
    if not rows:
        return None
    return {
        str(row["feature_code"]): float(row[value_column])
        for row in rows
    }


def _resolve_common_weight(
    rows: list[dict[str, Any]],
    *,
    input_source: str,
    default: float,
) -> float:
    source_rows = [row for row in rows if str(row["input_source"]) == input_source]
    feature_codes = {str(row["feature_code"]) for row in source_rows}
    weights = {float(row["weight"]) for row in source_rows}

    if feature_codes != _MVP_FEATURE_CODE_SET or len(source_rows) != len(MVP_FEATURE_CODES):
        return default
    if len(weights) != 1:
        return default
    return next(iter(weights))


@dataclass
class PostgresFeatureRuleRepository:
    """Read active Feature Rules for one semantic configuration version."""

    session: DatabaseSession

    def get_relationship_features(
        self,
        relationship_code: str,
        semantic_config_version_id: str,
    ) -> FeatureVector | None:
        rows = self.session.query(
            _RELATIONSHIP_FEATURE_SQL,
            (semantic_config_version_id, relationship_code),
        )
        return _rows_to_feature_vector(rows, value_column="feature_base_value")

    def get_occasion_features(
        self,
        occasion_code: str,
        semantic_config_version_id: str,
    ) -> FeatureVector | None:
        rows = self.session.query(
            _OCCASION_FEATURE_SQL,
            (semantic_config_version_id, occasion_code),
        )
        return _rows_to_feature_vector(rows, value_column="feature_base_value")

    def get_pair_delta(
        self,
        relationship_code: str,
        occasion_code: str,
        semantic_config_version_id: str,
    ) -> FeatureVector | None:
        pair_row = self.session.query_one(
            _PAIR_ID_SQL,
            (relationship_code, occasion_code),
        )
        if pair_row is None:
            return None

        rows = self.session.query(
            _PAIR_DELTA_SQL,
            (semantic_config_version_id, pair_row["pair_id"]),
        )
        return _rows_to_feature_vector(rows, value_column="feature_delta")

    def get_integration_weights(
        self,
        semantic_config_version_id: str,
    ) -> FeatureIntegrationWeights:
        rows = self.session.query(
            _INTEGRATION_WEIGHTS_SQL,
            (semantic_config_version_id,),
        )
        return FeatureIntegrationWeights(
            relationship_weight=_resolve_common_weight(
                rows,
                input_source="relationship_feature",
                default=DEFAULT_RELATIONSHIP_WEIGHT,
            ),
            occasion_weight=_resolve_common_weight(
                rows,
                input_source="occasion_feature",
                default=DEFAULT_OCCASION_WEIGHT,
            ),
        )
