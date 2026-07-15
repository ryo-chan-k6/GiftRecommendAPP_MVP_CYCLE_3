"""Unit tests for Postgres recommendation_result repositories."""

from __future__ import annotations

from datetime import UTC, datetime

from reco.application.recommendation_result_builder.models import (
    RecommendationResultHeaderInsertRow,
    ResultHeaderStatus,
)
from reco.application.result_snapshot_builder.models import (
    RecommendationResultItemInsertRow,
)
from reco.infrastructure.db.repositories.postgres_recommendation_result_item_repository import (
    PostgresRecommendationResultItemRepository,
)
from reco.infrastructure.db.repositories.postgres_recommendation_result_repository import (
    PostgresRecommendationResultRepository,
)
from unit.infrastructure.db.helpers import ScriptedDatabaseSession


def test_recommendation_result_repository_insert_header() -> None:
    session = ScriptedDatabaseSession(
        scripted_query_results=[[{"recommendation_result_id": "rr-1"}]],
    )
    row = RecommendationResultHeaderInsertRow(
        recommendation_result_id="rr-1",
        recommendation_request_id="req-1",
        recommendation_run_id="run-1",
        request_mode="ui",
        trace_id="trace-1",
        result_status=ResultHeaderStatus.GENERATED,
        top_k=10,
        result_item_count=1,
        candidate_count=3,
        fallback_used=False,
        semantic_config_version_id="sem-1",
        model_version_id="model-1",
        matching_config_id="match-1",
        ranking_config_id="rank-1",
        reason_template_version_id=None,
        generated_at=datetime(2026, 7, 15, tzinfo=UTC),
    )
    out = PostgresRecommendationResultRepository(session=session).insert_header(row)
    assert out is row
    assert session.operations[0][0] == "query"
    assert "matching_config_id" in session.operations[0][1]
    assert "match-1" in session.operations[0][2]


def test_recommendation_result_item_repository_insert_items() -> None:
    session = ScriptedDatabaseSession(affected_rows=1)
    rows = (
        RecommendationResultItemInsertRow(
            recommendation_result_item_id="rri-1",
            recommendation_result_id="rr-1",
            item_id="b1111111-1111-4111-8111-111111111001",
            rank=1,
            final_score=0.9,
            context_score=0.8,
            score_breakdown_json={"final": 0.9},
            is_displayed=True,
            is_fallback=False,
            item_name_snapshot="上品な焼き菓子ギフトセット",
            item_price_snapshot=4320,
            item_url_snapshot="https://example.com/items/1",
            item_image_url_snapshot="https://example.com/img.jpg",
            item_catchcopy_snapshot="贈る喜び",
            shop_name_snapshot="shop-001",
            review_average_snapshot=4.5,
            review_count_snapshot=12,
        ),
    )
    count = PostgresRecommendationResultItemRepository(session=session).insert_items(rows)
    assert count == 1
    assert session.operations[0][0] == "execute"


def test_recommendation_result_item_repository_empty() -> None:
    session = ScriptedDatabaseSession()
    assert PostgresRecommendationResultItemRepository(session=session).insert_items(()) == 0
