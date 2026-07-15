"""PostgreSQL recommendation_result header repository (MOD-RECO-021)."""

from __future__ import annotations

from dataclasses import dataclass

from reco.infrastructure.db.application_bootstrap import _load_application_module
from reco.infrastructure.db.session import DatabaseSession

_load_application_module(
    "reco.application.recommendation_result_builder",
    "recommendation-result-builder",
    "models",
)
from reco.application.recommendation_result_builder.models import (  # noqa: E402
    RecommendationResultHeaderInsertRow,
)

# matching_config_id は増分 migration で追加済み（20260702120000）。
_INSERT_SQL = """
INSERT INTO recommendation_result (
  recommendation_result_id,
  recommendation_request_id,
  recommendation_run_id,
  request_mode,
  result_status,
  top_k,
  result_item_count,
  candidate_count,
  fallback_used,
  semantic_config_version_id,
  model_version_id,
  matching_config_id,
  ranking_config_id,
  reason_template_version_id,
  trace_id,
  generated_at
) VALUES (
  %s, %s, %s, %s, %s,
  %s, %s, %s, %s, %s,
  %s, %s, %s, %s, %s,
  %s
)
RETURNING recommendation_result_id
"""


@dataclass
class PostgresRecommendationResultRepository:
    """IF-DB-RECO header INSERT for recommendation_result."""

    session: DatabaseSession

    def insert_header(
        self,
        row: RecommendationResultHeaderInsertRow,
    ) -> RecommendationResultHeaderInsertRow:
        inserted = self.session.query_one(
            _INSERT_SQL,
            (
                row.recommendation_result_id,
                row.recommendation_request_id,
                row.recommendation_run_id,
                row.request_mode,
                str(row.result_status),
                row.top_k,
                row.result_item_count,
                row.candidate_count,
                row.fallback_used,
                row.semantic_config_version_id,
                row.model_version_id,
                row.matching_config_id,
                row.ranking_config_id,
                row.reason_template_version_id,
                row.trace_id,
                row.generated_at,
            ),
        )
        if inserted is None:
            raise RuntimeError("recommendation_result insert failed")
        return row
