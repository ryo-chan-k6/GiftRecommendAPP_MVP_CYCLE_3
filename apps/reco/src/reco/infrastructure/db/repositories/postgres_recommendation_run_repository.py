"""PostgreSQL RecommendationRunRepository (MOD-RECO-002 / IF-DB-RECO-002)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from reco.domain.recommendation.run import RunStatus
from reco.infrastructure.db.session import DatabaseSession

from .recommendation_run_repository import (
    RecommendationRunRecord,
    RecommendationRunRepository,
)

_VERSION_EXISTS_SQL = """
SELECT
  EXISTS(
    SELECT 1
    FROM semantic_config_version
    WHERE semantic_config_version_id = %s
  ) AS semantic_exists,
  EXISTS(
    SELECT 1 FROM model_version WHERE model_version_id = %s
  ) AS model_exists,
  EXISTS(
    SELECT 1 FROM matching_config WHERE matching_config_id = %s
  ) AS matching_exists,
  EXISTS(
    SELECT 1 FROM ranking_config WHERE ranking_config_id = %s
  ) AS ranking_exists
"""

_INSERT_ACCEPTED_SQL = """
INSERT INTO recommendation_run (
  recommendation_request_id,
  pair_id,
  semantic_config_version_id,
  model_version_id,
  matching_config_id,
  ranking_config_id,
  run_status,
  created_at,
  updated_at
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING
  recommendation_run_id,
  recommendation_request_id,
  pair_id,
  semantic_config_version_id,
  model_version_id,
  matching_config_id,
  ranking_config_id,
  run_status,
  started_at,
  completed_at,
  created_at,
  updated_at
"""

_SELECT_BY_ID_SQL = """
SELECT
  recommendation_run_id,
  recommendation_request_id,
  pair_id,
  semantic_config_version_id,
  model_version_id,
  matching_config_id,
  ranking_config_id,
  run_status,
  started_at,
  completed_at,
  created_at,
  updated_at
FROM recommendation_run
WHERE recommendation_run_id = %s
"""

_UPDATE_STATUS_SQL = """
UPDATE recommendation_run
SET
  run_status = %s,
  started_at = %s,
  completed_at = %s,
  updated_at = %s
WHERE recommendation_run_id = %s
RETURNING
  recommendation_run_id,
  recommendation_request_id,
  pair_id,
  semantic_config_version_id,
  model_version_id,
  matching_config_id,
  ranking_config_id,
  run_status,
  started_at,
  completed_at,
  created_at,
  updated_at
"""


def _row_to_record(row: dict[str, object]) -> RecommendationRunRecord:
    return RecommendationRunRecord(
        run_id=str(row["recommendation_run_id"]),
        request_id=str(row["recommendation_request_id"]),
        pair_id=str(row["pair_id"]),
        semantic_config_version_id=str(row["semantic_config_version_id"]),
        model_version_id=str(row["model_version_id"]),
        matching_config_id=str(row["matching_config_id"]),
        ranking_config_id=str(row["ranking_config_id"]),
        run_status=RunStatus(str(row["run_status"])),
        started_at=row.get("started_at"),  # type: ignore[arg-type]
        completed_at=row.get("completed_at"),  # type: ignore[arg-type]
        created_at=row["created_at"],  # type: ignore[arg-type]
        updated_at=row["updated_at"],  # type: ignore[arg-type]
    )


@dataclass
class PostgresRecommendationRunRepository:
    """PostgreSQL implementation of ``RecommendationRunRepository``."""

    session: DatabaseSession

    def request_exists(self, request_id: str) -> bool:
        row = self.session.query_one(
            """
            SELECT 1 AS found
            FROM recommendation_request
            WHERE recommendation_request_id = %s
            """,
            (request_id,),
        )
        return row is not None

    def version_exists(
        self,
        *,
        semantic_config_version_id: str,
        model_version_id: str,
        matching_config_id: str,
        ranking_config_id: str,
    ) -> bool:
        row = self.session.query_one(
            _VERSION_EXISTS_SQL,
            (
                semantic_config_version_id,
                model_version_id,
                matching_config_id,
                ranking_config_id,
            ),
        )
        if row is None:
            return False
        return all(
            bool(row[key])
            for key in (
                "semantic_exists",
                "model_exists",
                "matching_exists",
                "ranking_exists",
            )
        )

    def insert_accepted(
        self,
        *,
        request_id: str,
        pair_id: str,
        semantic_config_version_id: str,
        model_version_id: str,
        matching_config_id: str,
        ranking_config_id: str,
    ) -> RecommendationRunRecord:
        now = datetime.now(UTC)
        row = self.session.query_one(
            _INSERT_ACCEPTED_SQL,
            (
                request_id,
                pair_id,
                semantic_config_version_id,
                model_version_id,
                matching_config_id,
                ranking_config_id,
                RunStatus.ACCEPTED.value,
                now,
                now,
            ),
        )
        if row is None:
            raise RuntimeError("insert failed")
        return _row_to_record(row)

    def get_by_id(self, run_id: str) -> RecommendationRunRecord | None:
        row = self.session.query_one(_SELECT_BY_ID_SQL, (run_id,))
        if row is None:
            return None
        return _row_to_record(row)

    def update_status(
        self,
        run_id: str,
        *,
        run_status: RunStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> RecommendationRunRecord:
        current = self.get_by_id(run_id)
        if current is None:
            raise KeyError(f"recommendation_run not found: {run_id}")

        now = datetime.now(UTC)
        row = self.session.query_one(
            _UPDATE_STATUS_SQL,
            (
                run_status.value,
                started_at if started_at is not None else current.started_at,
                completed_at if completed_at is not None else current.completed_at,
                now,
                run_id,
            ),
        )
        if row is None:
            raise RuntimeError("update failed")
        return _row_to_record(row)


def as_recommendation_run_repository(
    repository: PostgresRecommendationRunRepository,
) -> RecommendationRunRepository:
    """Narrow a concrete repository to the Protocol type."""

    return repository
