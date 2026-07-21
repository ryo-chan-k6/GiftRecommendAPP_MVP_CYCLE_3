"""Postgres-backed UserFeature repository for production composition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from reco.infrastructure.db.application_bootstrap import _load_application_module
from reco.infrastructure.db.session import DatabaseSession

_load_application_module(
    "reco.application.user_feature_generator",
    "user-feature-generator",
    "models",
)
from reco.application.user_feature_generator.models import (  # noqa: E402
    UserFeatureInsertRow,
)

_HAS_USER_SEMANTIC_SQL = """
SELECT 1 AS found
FROM user_semantic
WHERE recommendation_run_id = %s
"""

_SELECT_FOR_RUN_SQL = """
SELECT
  feature_code,
  feature_value,
  feature_normalization_version_id
FROM user_feature
WHERE recommendation_run_id = %s
ORDER BY feature_code
"""

_INSERT_COLUMNS = (
    "recommendation_run_id",
    "feature_code",
    "feature_normalization_version_id",
    "feature_value",
    "source_type",
    "generated_at",
)


@dataclass(frozen=True)
class PostgresUserFeatureRow:
    """Read model shared by MOD-RECO-008 / MOD-RECO-009 consistency checks."""

    feature_code: str
    feature_value: float
    feature_normalization_version_id: str


@dataclass
class PostgresAwareUserFeatureRepository:
    """UserFeature write/read + ``has_user_semantic`` against Postgres.

    Implements:
    - ``UserFeatureRepositoryPort`` (MOD-RECO-007)
    - ``UserFeatureReadPort`` (MOD-RECO-008 / MOD-RECO-009) via duck typing
    """

    session: DatabaseSession
    inserted_rows: list[UserFeatureInsertRow] = field(default_factory=list)
    should_fail_on_insert: bool = False
    reject_duplicate_insert: bool = True

    def has_user_semantic(self, recommendation_run_id: str) -> bool:
        row = self.session.query_one(
            _HAS_USER_SEMANTIC_SQL,
            (recommendation_run_id,),
        )
        return row is not None

    def get_user_features_for_run(
        self,
        recommendation_run_id: str,
    ) -> tuple[PostgresUserFeatureRow, ...]:
        rows = self.session.query(
            _SELECT_FOR_RUN_SQL,
            (recommendation_run_id,),
        )
        return tuple(
            PostgresUserFeatureRow(
                feature_code=str(row["feature_code"]),
                feature_value=_as_float(row["feature_value"]),
                feature_normalization_version_id=str(
                    row["feature_normalization_version_id"],
                ),
            )
            for row in rows
        )

    def insert_user_features(self, rows: tuple[UserFeatureInsertRow, ...]) -> None:
        if self.should_fail_on_insert:
            raise RuntimeError("user_feature insert failed")
        if not rows:
            return
        if self.reject_duplicate_insert:
            run_id = rows[0].recommendation_run_id
            if any(row.recommendation_run_id == run_id for row in self.inserted_rows):
                raise RuntimeError("duplicate user_feature insert for run")
            existing = self.get_user_features_for_run(run_id)
            if existing:
                raise RuntimeError("duplicate user_feature insert for run")

        placeholders = ", ".join(
            ["(" + ", ".join(["%s"] * len(_INSERT_COLUMNS)) + ")"] * len(rows),
        )
        sql = (
            "INSERT INTO user_feature ("
            + ", ".join(_INSERT_COLUMNS)
            + f") VALUES {placeholders}"
        )
        params: list[Any] = []
        for row in rows:
            params.extend(
                (
                    row.recommendation_run_id,
                    row.feature_code,
                    row.feature_normalization_version_id,
                    row.feature_value,
                    row.source_type,
                    row.generated_at,
                ),
            )
        affected = self.session.execute(sql, tuple(params))
        if affected != len(rows):
            raise RuntimeError(
                f"user_feature insert rowcount mismatch: expected {len(rows)}, got {affected}",
            )
        self.inserted_rows.extend(rows)


def _as_float(value: Any) -> float:
    return float(value)
