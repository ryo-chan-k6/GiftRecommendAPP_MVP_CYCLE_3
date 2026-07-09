"""Postgres observability module wiring for production composition."""

from __future__ import annotations

from dataclasses import dataclass

from reco.application.error_log_writer import ErrorLogWriter
from reco.application.metric_logger import MetricLogger
from reco.application.phase_log_writer import PhaseLogWriter
from reco.application.reco_error_handler import RecoErrorHandler
from reco.application.recommendation_run_recorder import (
    SCAFFOLD_PAIR_ID,
    SCAFFOLD_PAIR_KEY,
    RecommendationRunRecorder,
)
from reco.infrastructure.db.repositories.pair_master_reader import InMemoryPairMasterReader
from reco.infrastructure.db.repositories.postgres_error_log_repository import (
    PostgresErrorLogRepository,
)
from reco.infrastructure.db.repositories.postgres_metric_log_repository import (
    PostgresMetricLogRepository,
    as_metric_logger_repository,
)
from reco.infrastructure.db.repositories.postgres_phase_log_repository import (
    PostgresPhaseLogRepository,
)
from reco.infrastructure.db.repositories.postgres_reco_score_distribution_metric_repository import (
    PostgresScoreDistributionMetricRepository,
)
from reco.infrastructure.db.repositories.postgres_recommendation_run_repository import (
    PostgresRecommendationRunRepository,
    as_recommendation_run_repository,
)
from reco.infrastructure.db.session import DatabaseSession
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


@dataclass(frozen=True)
class ObservabilityRepositories:
    """Postgres repositories for MOD-RECO-002 / 028 / 029 / 025 observability."""

    run_repository: PostgresRecommendationRunRepository
    phase_log_repository: PostgresPhaseLogRepository
    error_log_repository: PostgresErrorLogRepository
    metric_log_repository: PostgresMetricLogRepository
    score_distribution_metric_repository: PostgresScoreDistributionMetricRepository


def build_observability_repositories(
    session: DatabaseSession,
) -> ObservabilityRepositories:
    """Create Postgres observability repositories from a database session."""

    return ObservabilityRepositories(
        run_repository=PostgresRecommendationRunRepository(session=session),
        phase_log_repository=PostgresPhaseLogRepository(session=session),
        error_log_repository=PostgresErrorLogRepository(session=session),
        metric_log_repository=PostgresMetricLogRepository(session=session),
        score_distribution_metric_repository=PostgresScoreDistributionMetricRepository(
            session=session,
        ),
    )


def build_production_observability_modules(
    session: DatabaseSession,
) -> dict[str, object]:
    """Wire observability application modules to Postgres repositories."""

    repositories = build_observability_repositories(session)

    run_recorder = RecommendationRunRecorder(
        run_repository=as_recommendation_run_repository(repositories.run_repository),
        pair_reader=InMemoryPairMasterReader(
            pairs={SCAFFOLD_PAIR_KEY: SCAFFOLD_PAIR_ID},
        ),
        logger=ScaffoldRecoLogger(),
    )
    phase_log_writer = PhaseLogWriter(
        repository=repositories.phase_log_repository,
        logger=ScaffoldRecoLogger(),
    )
    error_handler = RecoErrorHandler(
        error_log_writer=ErrorLogWriter(
            repository=repositories.error_log_repository,
            logger=ScaffoldRecoLogger(),
        ),
        logger=ScaffoldRecoLogger(),
        append_test_seam_events=True,
    )
    metric_logger = MetricLogger(
        repository=as_metric_logger_repository(repositories.metric_log_repository),
        logger=ScaffoldRecoLogger(),
    )

    return {
        "database_session": session,
        "observability_repositories": repositories,
        "score_distribution_metric_repository": (
            repositories.score_distribution_metric_repository
        ),
        "run_recorder": run_recorder,
        "phase_log_writer": phase_log_writer,
        "error_handler": error_handler,
        "metric_logger": metric_logger,
    }
