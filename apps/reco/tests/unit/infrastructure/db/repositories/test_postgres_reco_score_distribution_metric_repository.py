"""Postgres ScoreDistributionMetricRepository unit tests."""

from __future__ import annotations

from datetime import UTC, datetime

from reco.infrastructure.db.repositories.postgres_reco_score_distribution_metric_repository import (
    PostgresScoreDistributionMetricRepository,
    ScoreDistributionMetricRecord,
)
from unit.infrastructure.db.helpers import ScriptedDatabaseSession


def _distribution_record(
    *,
    score_type: str = "context_score",
) -> ScoreDistributionMetricRecord:
    return ScoreDistributionMetricRecord(
        recommendation_run_id="550e8400-e29b-41d4-a716-446655440000",
        recommendation_result_id="660e8400-e29b-41d4-a716-446655440001",
        semantic_config_version_id="770e8400-e29b-41d4-a716-446655440002",
        ranking_config_id="880e8400-e29b-41d4-a716-446655440003",
        score_type=score_type,  # type: ignore[arg-type]
        sample_count=5,
        mean=0.42,
        stddev=0.1,
        min_value=0.2,
        max_value=0.8,
        p10=0.25,
        p50=0.4,
        p90=0.7,
        calculated_at=datetime.now(UTC),
    )


def test_upsert_targets_reco_score_distribution_metric_only() -> None:
    session = ScriptedDatabaseSession(affected_rows=1)
    repository = PostgresScoreDistributionMetricRepository(session=session)

    repository.upsert(_distribution_record(score_type="final_score"))

    sql = session.operations[0][1]
    params = session.operations[0][2]
    assert "INSERT INTO reco_score_distribution_metric" in sql
    assert "'run'" in sql
    assert "metric_log" not in sql
    assert params[4] == "final_score"


def test_tier2_supports_context_and_final_score_types() -> None:
    for score_type in ("context_score", "final_score"):
        record = _distribution_record(score_type=score_type)
        assert record.score_type == score_type
