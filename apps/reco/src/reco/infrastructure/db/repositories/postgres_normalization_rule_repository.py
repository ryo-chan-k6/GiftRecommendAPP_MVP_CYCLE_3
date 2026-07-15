"""PostgreSQL NormalizationRuleRepository for MOD-RECO-007."""

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
    NormalizationBinding,
)

_BINDING_SQL = """
SELECT
  nr.feature_normalization_version_id,
  nr.normalization_method,
  fnv.parameter_json
FROM normalization_rule AS nr
JOIN feature_normalization_version AS fnv
  ON fnv.feature_normalization_version_id = nr.feature_normalization_version_id
WHERE nr.semantic_config_version_id = %s
  AND nr.is_active = true
LIMIT 1
"""

_CURRENT_FALLBACK_SQL = """
SELECT
  feature_normalization_version_id,
  normalization_method,
  parameter_json
FROM feature_normalization_version
WHERE normalization_method = 'sigmoid'
  AND is_current = true
LIMIT 1
"""


def _as_parameter_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    raise TypeError(f"parameter_json must be object, got {type(value)!r}")


@dataclass
class PostgresNormalizationRuleRepository:
    """Resolve Feature normalization binding from Postgres.

    Preferred path: ``normalization_rule`` × ``feature_normalization_version``.
    Fallback (seed gap): current sigmoid ``feature_normalization_version`` when
    ``normalization_rule`` has no active row for the semantic version.
    """

    session: DatabaseSession

    def get_active_normalization_binding(
        self,
        semantic_config_version_id: str,
    ) -> NormalizationBinding | None:
        row = self.session.query_one(
            _BINDING_SQL,
            (semantic_config_version_id,),
        )
        if row is None:
            row = self.session.query_one(_CURRENT_FALLBACK_SQL)
        if row is None:
            return None

        params = _as_parameter_json(row["parameter_json"])
        return NormalizationBinding(
            feature_normalization_version_id=str(
                row["feature_normalization_version_id"],
            ),
            parameters=FeatureNormalizationParameters(
                center_feature=float(params["center_feature"]),
                k_feature=float(params["k_feature"]),
                normalization_method=str(row["normalization_method"]),
            ),
        )
