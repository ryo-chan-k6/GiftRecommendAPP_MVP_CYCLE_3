"""Postgres MetricLogRepository unit tests."""

from __future__ import annotations

from datetime import UTC, datetime

from reco.application.metric_logger.models import MetricRecord
from reco.infrastructure.db.repositories.postgres_metric_log_repository import (
    PostgresMetricLogRepository,
)
from unit.infrastructure.db.helpers import ScriptedDatabaseSession


def _metric_record() -> MetricRecord:
    return MetricRecord(
        recommendation_run_id="550e8400-e29b-41d4-a716-446655440000",
        trace_id="trace-1",
        recommendation_latency_ms=120,
        pre_filter_candidate_count=40,
        retrieval_candidate_count=30,
        post_filter_candidate_count=18,
        final_result_count=10,
        recommendation_empty=False,
        reason_fallback_count=1,
        retrieval_phase_latency_ms=20,
        matching_latency_ms=30,
        ranking_latency_ms=25,
        reason_generation_latency_ms=15,
        recorded_at=datetime.now(UTC),
        metric_source="MOD-RECO-025",
    )


def test_save_inserts_metric_log_columns() -> None:
    session = ScriptedDatabaseSession(affected_rows=1)
    repository = PostgresMetricLogRepository(session=session)
    record = _metric_record()

    repository.save(record)

    assert session.operations[0][0] == "execute"
    sql = session.operations[0][1]
    params = session.operations[0][2]
    assert "INSERT INTO metric_log" in sql
    assert "reco_score_distribution_metric" not in sql
    assert params[0] == record.trace_id
    assert params[1] == record.recommendation_run_id
    assert params[-1] == "MOD-RECO-025"


def test_metric_record_fields_align_with_metric_log_columns() -> None:
    record = _metric_record()
    expected_columns = (
        "trace_id",
        "recommendation_run_id",
        "recommendation_latency_ms",
        "pre_filter_candidate_count",
        "retrieval_candidate_count",
        "post_filter_candidate_count",
        "final_result_count",
        "recommendation_empty",
        "reason_fallback_count",
        "retrieval_phase_latency_ms",
        "matching_latency_ms",
        "ranking_latency_ms",
        "reason_generation_latency_ms",
        "recorded_at",
        "metric_source",
    )
    for column in expected_columns:
        assert hasattr(record, column)
