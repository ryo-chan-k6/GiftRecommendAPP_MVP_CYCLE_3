"""Composition root builder unit tests."""

from __future__ import annotations

from dataclasses import replace

from reco.application.error_log_writer import ErrorLogWriter
from reco.application.metric_logger import MetricLogger
from reco.application.phase_log_writer import PhaseLogWriter
from reco.application.reco_error_handler import RecoErrorHandler
from reco.application.recommendation_orchestrator import build_default_stub_ports
from reco.application.recommendation_run_recorder import RecommendationRunRecorder
from reco.composition import (
    CompositionMode,
    ObservabilityRepositories,
    build_composition_ports,
    build_production_ports,
)
from reco.composition.observability import build_production_observability_modules
from reco.application.config_version_resolver import ProductionConfigRepository
from reco.infrastructure.db.repositories.pair_master_reader import (
    InMemoryPairMasterReader,
    PostgresPairMasterReader,
)
from reco.infrastructure.db.repositories.postgres_error_log_repository import (
    PostgresErrorLogRepository,
)
from reco.infrastructure.db.repositories.postgres_metric_log_repository import (
    PostgresMetricLogRepository,
)
from reco.infrastructure.db.repositories.postgres_phase_log_repository import (
    PostgresPhaseLogRepository,
)
from reco.infrastructure.db.repositories.postgres_reco_score_distribution_metric_repository import (
    PostgresScoreDistributionMetricRepository,
)
from reco.infrastructure.db.repositories.postgres_recommendation_run_repository import (
    PostgresRecommendationRunRepository,
)
from reco.infrastructure.db.session import ScaffoldDatabaseSession


def test_build_composition_ports_default_delegates_to_stub_builder() -> None:
    expected_ports, expected_helpers = build_default_stub_ports()
    ports, helpers = build_composition_ports(CompositionMode.DEFAULT)

    assert type(ports.run_recorder) is type(expected_ports.run_recorder)
    assert isinstance(ports.run_recorder.pair_reader, InMemoryPairMasterReader)
    assert type(ports.metric_logger) is type(expected_ports.metric_logger)
    assert set(helpers) == set(expected_helpers)


def test_build_production_ports_replaces_observability_and_config_resolver() -> None:
    default_ports, _ = build_default_stub_ports()
    session = ScaffoldDatabaseSession(backend="scaffold-production-test")

    ports, helpers = build_production_ports(database_session=session)

    assert type(ports.run_recorder) is RecommendationRunRecorder
    assert isinstance(ports.run_recorder.pair_reader, PostgresPairMasterReader)
    assert type(ports.phase_log_writer) is PhaseLogWriter
    assert type(ports.error_handler) is RecoErrorHandler
    assert type(ports.metric_logger) is MetricLogger
    assert isinstance(ports.config_resolver.repository, ProductionConfigRepository)
    assert ports.config_resolver is not default_ports.config_resolver

    assert type(default_ports.candidate_retriever) is type(ports.candidate_retriever)
    assert type(default_ports.reason_generator) is type(ports.reason_generator)

    repositories = helpers["observability_repositories"]
    assert isinstance(repositories, ObservabilityRepositories)
    assert isinstance(repositories.run_repository, PostgresRecommendationRunRepository)
    assert isinstance(repositories.phase_log_repository, PostgresPhaseLogRepository)
    assert isinstance(repositories.error_log_repository, PostgresErrorLogRepository)
    assert isinstance(repositories.metric_log_repository, PostgresMetricLogRepository)
    assert isinstance(
        repositories.score_distribution_metric_repository,
        PostgresScoreDistributionMetricRepository,
    )
    assert helpers["config_repository"] is ports.config_resolver.repository


def test_build_production_observability_modules_wires_postgres_repositories() -> None:
    session = ScaffoldDatabaseSession(backend="scaffold-observability-test")
    modules = build_production_observability_modules(session)

    run_recorder = modules["run_recorder"]
    assert isinstance(run_recorder, RecommendationRunRecorder)
    assert isinstance(run_recorder.run_repository, PostgresRecommendationRunRepository)
    assert isinstance(run_recorder.pair_reader, PostgresPairMasterReader)

    phase_log_writer = modules["phase_log_writer"]
    assert isinstance(phase_log_writer, PhaseLogWriter)
    assert isinstance(phase_log_writer.repository, PostgresPhaseLogRepository)

    error_handler = modules["error_handler"]
    assert isinstance(error_handler, RecoErrorHandler)
    error_log_writer = error_handler.error_log_writer
    assert isinstance(error_log_writer, ErrorLogWriter)
    assert isinstance(error_log_writer.repository, PostgresErrorLogRepository)

    metric_logger = modules["metric_logger"]
    assert isinstance(metric_logger, MetricLogger)
    assert isinstance(metric_logger.repository, PostgresMetricLogRepository)


def test_build_composition_ports_production_selects_postgres_observability() -> None:
    session = ScaffoldDatabaseSession(backend="scaffold-composition-test")

    ports, helpers = build_composition_ports(
        CompositionMode.PRODUCTION,
        database_session=session,
    )

    assert isinstance(ports.run_recorder, RecommendationRunRecorder)
    assert isinstance(ports.run_recorder.pair_reader, PostgresPairMasterReader)
    assert isinstance(
        helpers["score_distribution_metric_repository"],
        PostgresScoreDistributionMetricRepository,
    )


def test_build_production_ports_helpers_expose_tier_2_repository_alias() -> None:
    session = ScaffoldDatabaseSession(backend="scaffold-tier2-test")
    _, helpers = build_production_ports(database_session=session)
    repositories = helpers["observability_repositories"]
    assert isinstance(repositories, ObservabilityRepositories)

    assert helpers["score_distribution_metric_repository"] is (
        repositories.score_distribution_metric_repository
    )


def test_build_production_ports_preserves_non_observability_ports_from_default() -> None:
    default_ports, _ = build_default_stub_ports()
    session = ScaffoldDatabaseSession(backend="scaffold-non-obs-test")

    ports, _ = build_production_ports(database_session=session)
    expected = replace(
        default_ports,
        config_resolver=ports.config_resolver,
        run_recorder=ports.run_recorder,
        phase_log_writer=ports.phase_log_writer,
        error_handler=ports.error_handler,
        metric_logger=ports.metric_logger,
    )

    assert isinstance(ports.config_resolver.repository, ProductionConfigRepository)
    assert type(expected.final_ranker) is type(ports.final_ranker)
    assert type(expected.snapshot_builder) is type(ports.snapshot_builder)
