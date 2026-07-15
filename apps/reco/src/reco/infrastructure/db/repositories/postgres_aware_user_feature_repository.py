"""Postgres-aware UserFeatureRepository for production composition."""

from __future__ import annotations

from dataclasses import dataclass, field

from reco.application.user_feature_generator.models import UserFeatureInsertRow
from reco.infrastructure.db.session import DatabaseSession

_HAS_USER_SEMANTIC_SQL = """
SELECT 1 AS found
FROM user_semantic
WHERE recommendation_run_id = %s
"""


@dataclass
class PostgresAwareUserFeatureRepository:
    """UserFeatureRepositoryPort with Postgres-backed ``has_user_semantic``.

    ``insert_user_features`` remains in-memory for this Task (full user_feature
    persistence is deferred). MOD-RECO-007 prerequisite checks only read the
    ``user_semantic`` table.
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

    def insert_user_features(self, rows: tuple[UserFeatureInsertRow, ...]) -> None:
        if self.should_fail_on_insert:
            raise RuntimeError("user_feature insert failed")
        if self.reject_duplicate_insert and rows:
            run_id = rows[0].recommendation_run_id
            if any(row.recommendation_run_id == run_id for row in self.inserted_rows):
                raise RuntimeError("duplicate user_feature insert for run")
        self.inserted_rows.extend(rows)
