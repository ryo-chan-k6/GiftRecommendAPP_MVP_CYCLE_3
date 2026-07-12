"""MOD-RECO-001 §14 No.10 Postgres observability E2E integration tests."""

from __future__ import annotations

from dataclasses import replace

import pytest

from reco.application.metric_logger.constants import METRIC_SOURCE, TIER_2_METRIC_PREFIXES
from reco.application.recommendation_orchestrator import RecommendationOrchestrator
from reco.application.recommendation_orchestrator.stubs import StubPipelineModule
from reco.composition.builder import build_composition_ports
from reco.composition.config import CompositionMode
from reco.domain import RunStatus
from reco.infrastructure.db.session import DatabaseSession

from helpers.postgres_bootstrap import (
    build_composition_ports_production_for_postgres,
    build_production_ports_for_postgres,
    count_reco_score_distribution_metrics,
    fetch_error_logs_for_trace,
    fetch_metric_log_for_run,
    fetch_phase_logs_for_run,
    fetch_recommendation_run,
    insert_recommendation_request,
    new_request_id,
    sample_integration_request,
)
from recommendation_orchestrator_helpers import build_wired_default_composition_ports

pytestmark = pytest.mark.postgres_integration


def test_build_composition_ports_production_matches_build_production_ports(
    postgres_session: DatabaseSession,
) -> None:
    """CompositionMode.PRODUCTION と build_production_ports() が同一 observability 配線であること。"""
    from_ports, _ = build_production_ports_for_postgres(postgres_session)
    composition_ports, _ = build_composition_ports_production_for_postgres(postgres_session)

    assert type(from_ports.run_recorder) is type(composition_ports.run_recorder)
    assert type(from_ports.phase_log_writer) is type(composition_ports.phase_log_writer)
    assert type(from_ports.error_handler) is type(composition_ports.error_handler)
    assert type(from_ports.metric_logger) is type(composition_ports.metric_logger)


def test_section14_no10_success_run_persists_run_phase_and_tier1_metric_to_postgres(
    postgres_session: DatabaseSession,
) -> None:
    """§14 No.10: 本番 composition 成功 Run で Run / Phase / Tier 1 Metric が Postgres に永続化される。"""
    request_id = new_request_id()
    trace_id = f"trace-section14-no10-success-{request_id[:8]}"
    insert_recommendation_request(
        postgres_session,
        request_id=request_id,
        trace_id=trace_id,
    )

    ports, helpers = build_production_ports_for_postgres(postgres_session)
    outcome = RecommendationOrchestrator(ports).run(
        sample_integration_request(request_id=request_id),
        trace_id=trace_id,
    )

    assert outcome.success is True
    context = outcome.execution_context
    assert context is not None
    run_id = context.run_id
    assert run_id is not None

    run_row = fetch_recommendation_run(postgres_session, run_id)
    assert run_row is not None
    assert str(run_row["recommendation_request_id"]) == request_id
    assert run_row["run_status"] in {"running", "succeeded"}

    phase_rows = fetch_phase_logs_for_run(postgres_session, run_id)
    assert phase_rows
    assert all(str(row["trace_id"]) == trace_id for row in phase_rows)
    assert all(str(row["owner_id"]) == run_id for row in phase_rows)

    metric_row = fetch_metric_log_for_run(postgres_session, run_id)
    assert metric_row is not None
    assert str(metric_row["trace_id"]) == trace_id
    assert str(metric_row["recommendation_run_id"]) == run_id
    assert metric_row["final_result_count"] == 2
    assert metric_row["recommendation_empty"] is False
    assert metric_row["metric_source"] == METRIC_SOURCE

    assert count_reco_score_distribution_metrics(postgres_session, run_id) == 0

    metric_logger = helpers["metric_logger"]
    assert len(metric_logger.recorded) == 1
    observation = metric_logger.recorded[0]
    for key in observation:
        assert not any(
            key == prefix or key.startswith(f"{prefix}_")
            for prefix in TIER_2_METRIC_PREFIXES
        )

    assert fetch_error_logs_for_trace(postgres_session, trace_id) == []


def test_section14_no10_failure_run_persists_error_and_phase_without_metric(
    postgres_session: DatabaseSession,
) -> None:
    """§14 No.10: 本番 composition 失敗 Run で Error / Phase が Postgres に記録され Metric は空。"""
    request_id = new_request_id()
    trace_id = f"trace-section14-no10-failure-{request_id[:8]}"
    insert_recommendation_request(
        postgres_session,
        request_id=request_id,
        trace_id=trace_id,
    )

    ports, helpers = build_production_ports_for_postgres(postgres_session)
    ports = replace(
        ports,
        user_semantic_extractor=StubPipelineModule(
            module_id="MOD-RECO-004",
            phase_name="semantic_extracted",
            should_fail=True,
        ),
    )

    outcome = RecommendationOrchestrator(ports).run(
        sample_integration_request(request_id=request_id),
        trace_id=trace_id,
    )

    assert outcome.success is False
    assert outcome.reco_error is not None
    assert outcome.reco_error.error_code == "GRS-REC-004"
    context = outcome.execution_context
    assert context is not None
    run_id = context.run_id
    assert run_id is not None

    run_row = fetch_recommendation_run(postgres_session, run_id)
    assert run_row is not None
    assert str(run_row["recommendation_request_id"]) == request_id

    error_rows = fetch_error_logs_for_trace(postgres_session, trace_id)
    assert len(error_rows) == 1
    assert error_rows[0]["error_code"] == "GRS-REC-004"
    assert str(error_rows[0]["request_id"]) == request_id

    phase_rows = fetch_phase_logs_for_run(postgres_session, run_id)
    assert phase_rows
    assert any(row["phase_status"] == "failed" for row in phase_rows)
    assert all(str(row["trace_id"]) == trace_id for row in phase_rows)

    assert fetch_metric_log_for_run(postgres_session, run_id) is None
    assert count_reco_score_distribution_metrics(postgres_session, run_id) == 0
    assert helpers["metric_logger"].recorded == []


def test_mvp_default_composition_unchanged_after_production_builder_exists() -> None:
    """MVP デフォルト composition（build_default_stub_ports 経路）が削除されていないこと。"""
    from reco.application.metric_logger.repository import InMemoryMetricLoggerRepository
    from reco.infrastructure.db.repositories.recommendation_run_repository import (
        InMemoryRecommendationRunRepository,
    )

    ports, helpers = build_wired_default_composition_ports()
    assert ports.run_recorder is not None
    assert helpers["metric_logger"] is not None
    assert isinstance(
        ports.run_recorder.run_repository,
        InMemoryRecommendationRunRepository,
    )
    assert isinstance(
        helpers["metric_logger"].repository,
        InMemoryMetricLoggerRepository,
    )

    production_ports, _ = build_composition_ports(CompositionMode.PRODUCTION)
    from reco.infrastructure.db.repositories.postgres_metric_log_repository import (
        PostgresMetricLogRepository,
    )
    from reco.infrastructure.db.repositories.postgres_recommendation_run_repository import (
        PostgresRecommendationRunRepository,
    )

    assert isinstance(
        production_ports.run_recorder.run_repository,
        PostgresRecommendationRunRepository,
    )
    assert isinstance(
        production_ports.metric_logger.repository,
        PostgresMetricLogRepository,
    )
