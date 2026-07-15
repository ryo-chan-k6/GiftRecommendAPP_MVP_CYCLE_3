"""PostgreSQL UserSemanticRepository (MOD-RECO-004 / IF-DB-RECO-003)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from psycopg.types.json import Json

from reco.application.user_semantic_extractor.models import UserSemanticRecord
from reco.infrastructure.db.session import DatabaseSession

_EXISTS_SQL = """
SELECT 1 AS found
FROM user_semantic
WHERE recommendation_run_id = %s
"""

_INSERT_SQL = """
INSERT INTO user_semantic (
  recommendation_run_id,
  semantic_config_version_id,
  extracted_semantic_json,
  generated_at
) VALUES (%s, %s, %s, %s)
RETURNING
  user_semantic_id,
  recommendation_run_id,
  semantic_config_version_id,
  extracted_semantic_json,
  generated_at
"""


def _as_json_object(value: Any) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    raise TypeError(f"extracted_semantic_json must be object, got {type(value)!r}")


@dataclass
class PostgresUserSemanticRepository:
    """Persist user_semantic rows to Postgres (production composition)."""

    session: DatabaseSession

    def exists_for_run(self, recommendation_run_id: str) -> bool:
        row = self.session.query_one(_EXISTS_SQL, (recommendation_run_id,))
        return row is not None

    def insert(
        self,
        *,
        recommendation_run_id: str,
        semantic_config_version_id: str,
        extracted_semantic_json: dict[str, object],
    ) -> UserSemanticRecord:
        generated_at = datetime.now(UTC)
        row = self.session.query_one(
            _INSERT_SQL,
            (
                recommendation_run_id,
                semantic_config_version_id,
                Json(extracted_semantic_json),
                generated_at,
            ),
        )
        if row is None:
            raise RuntimeError("user_semantic insert failed")
        return UserSemanticRecord(
            user_semantic_id=str(row["user_semantic_id"]),
            recommendation_run_id=str(row["recommendation_run_id"]),
            semantic_config_version_id=str(row["semantic_config_version_id"]),
            extracted_semantic_json=_as_json_object(row["extracted_semantic_json"]),
            generated_at=row["generated_at"],
        )
