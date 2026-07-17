"""PostgreSQL recommendation_reason repository (MOD-RECO-023 / IF-DB-RECO-008)."""

from __future__ import annotations

from dataclasses import dataclass

from psycopg.types.json import Json

from reco.infrastructure.db.application_bootstrap import _load_application_module
from reco.infrastructure.db.session import DatabaseSession

_load_application_module(
    "reco.application.reason_generator",
    "reason-generator",
    "models",
)
from reco.application.reason_generator.models import (  # noqa: E402
    RecommendationReasonInsertRow,
)

_INSERT_SQL = """
INSERT INTO recommendation_reason (
  recommendation_reason_id,
  recommendation_result_item_id,
  template_id,
  reason_summary,
  reason_detail,
  reason_points_json,
  reason_badges_json,
  caution_note,
  reason_basis_json
) VALUES (
  %s, %s, %s, %s, %s,
  %s, %s, %s, %s
)
"""


@dataclass
class PostgresRecommendationReasonRepository:
    """IF-DB-RECO-008 recommendation_reason INSERT."""

    session: DatabaseSession

    def insert(self, row: RecommendationReasonInsertRow) -> RecommendationReasonInsertRow:
        affected = self.session.execute(
            _INSERT_SQL,
            (
                row.recommendation_reason_id,
                row.recommendation_result_item_id,
                row.template_id,
                row.reason_summary,
                row.reason_detail,
                Json(row.reason_points_json)
                if row.reason_points_json is not None
                else None,
                Json(row.reason_badges_json)
                if row.reason_badges_json is not None
                else None,
                row.caution_note,
                Json(row.reason_basis_json),
            ),
        )
        if affected < 1:
            raise RuntimeError(
                "recommendation_reason insert failed: "
                f"{row.recommendation_reason_id}",
            )
        return row
