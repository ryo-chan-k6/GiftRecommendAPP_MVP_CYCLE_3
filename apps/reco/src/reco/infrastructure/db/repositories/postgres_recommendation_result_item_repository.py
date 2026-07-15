"""PostgreSQL recommendation_result_item repository (MOD-RECO-022)."""

from __future__ import annotations

from dataclasses import dataclass

from psycopg.types.json import Json

from reco.infrastructure.db.application_bootstrap import _load_application_module
from reco.infrastructure.db.session import DatabaseSession

_load_application_module(
    "reco.application.result_snapshot_builder",
    "result-snapshot-builder",
    "models",
)
from reco.application.result_snapshot_builder.models import (  # noqa: E402
    RecommendationResultItemInsertRow,
)

_INSERT_SQL = """
INSERT INTO recommendation_result_item (
  recommendation_result_item_id,
  recommendation_result_id,
  item_id,
  rank,
  final_score,
  context_score,
  score_breakdown_json,
  item_name_snapshot,
  item_catchcopy_snapshot,
  item_price_snapshot,
  item_url_snapshot,
  item_image_url_snapshot,
  review_average_snapshot,
  review_count_snapshot,
  shop_name_snapshot,
  is_displayed,
  is_fallback
) VALUES (
  %s, %s, %s, %s, %s,
  %s, %s, %s, %s, %s,
  %s, %s, %s, %s, %s,
  %s, %s
)
"""


@dataclass
class PostgresRecommendationResultItemRepository:
    """IF-DB-RECO item INSERT for recommendation_result_item."""

    session: DatabaseSession

    def insert_items(
        self,
        rows: tuple[RecommendationResultItemInsertRow, ...],
    ) -> int:
        if not rows:
            return 0
        for row in rows:
            affected = self.session.execute(
                _INSERT_SQL,
                (
                    row.recommendation_result_item_id,
                    row.recommendation_result_id,
                    row.item_id,
                    row.rank,
                    row.final_score,
                    row.context_score,
                    Json(row.score_breakdown_json)
                    if row.score_breakdown_json is not None
                    else None,
                    row.item_name_snapshot,
                    row.item_catchcopy_snapshot,
                    row.item_price_snapshot,
                    row.item_url_snapshot,
                    row.item_image_url_snapshot,
                    row.review_average_snapshot,
                    row.review_count_snapshot,
                    row.shop_name_snapshot,
                    row.is_displayed,
                    row.is_fallback,
                ),
            )
            if affected < 1:
                raise RuntimeError(
                    "recommendation_result_item insert failed: "
                    f"{row.recommendation_result_item_id}",
                )
        return len(rows)
