"""Unit tests for Postgres recommendation_reason repository."""

from __future__ import annotations

from reco.application.reason_generator.models import RecommendationReasonInsertRow
from reco.infrastructure.db.repositories.postgres_recommendation_reason_repository import (
    PostgresRecommendationReasonRepository,
)
from unit.infrastructure.db.helpers import ScriptedDatabaseSession


def test_recommendation_reason_repository_insert() -> None:
    session = ScriptedDatabaseSession(affected_rows=1)
    row = RecommendationReasonInsertRow(
        recommendation_reason_id="rrn-1",
        recommendation_result_item_id="rri-1",
        template_id="tpl-1",
        reason_summary="バランスが良いため",
        reason_detail="短文の詳細",
        reason_points_json=["上品", "安心"],
        reason_badges_json=["上品"],
        caution_note=None,
        reason_basis_json={
            "generation_method": "template",
            "used_features": [],
            "template_name": "default_summary",
            "template_version": 1,
        },
    )
    out = PostgresRecommendationReasonRepository(session=session).insert(row)
    assert out is row
    assert session.operations[0][0] == "execute"
    assert "recommendation_reason" in session.operations[0][1]


def test_recommendation_reason_repository_insert_failure() -> None:
    session = ScriptedDatabaseSession(affected_rows=0)
    row = RecommendationReasonInsertRow(
        recommendation_reason_id="rrn-2",
        recommendation_result_item_id="rri-2",
        template_id="tpl-1",
        reason_summary="汎用理由",
        reason_detail=None,
        reason_points_json=None,
        reason_badges_json=None,
        caution_note=None,
        reason_basis_json={"generation_method": "reason_module_internal_fallback"},
    )
    try:
        PostgresRecommendationReasonRepository(session=session).insert(row)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "recommendation_reason insert failed" in str(exc)
