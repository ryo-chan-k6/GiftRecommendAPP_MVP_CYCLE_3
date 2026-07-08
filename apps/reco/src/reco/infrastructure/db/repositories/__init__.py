"""Database repositories for reco infrastructure."""

from reco.infrastructure.db.repositories.pair_master_reader import (
    InMemoryPairMasterReader,
    PairMasterReader,
)
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
    ScoreDistributionMetricRecord,
    ScoreDistributionMetricRepository,
    as_score_distribution_metric_repository,
)
from reco.infrastructure.db.repositories.postgres_recommendation_run_repository import (
    PostgresRecommendationRunRepository,
    as_recommendation_run_repository,
)
from reco.infrastructure.db.repositories.recommendation_run_repository import (
    InMemoryRecommendationRunRepository,
    RecommendationRunRecord,
    RecommendationRunRepository,
)

__all__ = [
    "InMemoryPairMasterReader",
    "InMemoryRecommendationRunRepository",
    "PairMasterReader",
    "PostgresErrorLogRepository",
    "PostgresMetricLogRepository",
    "PostgresPhaseLogRepository",
    "PostgresRecommendationRunRepository",
    "PostgresScoreDistributionMetricRepository",
    "RecommendationRunRecord",
    "RecommendationRunRepository",
    "ScoreDistributionMetricRecord",
    "ScoreDistributionMetricRepository",
    "as_metric_logger_repository",
    "as_recommendation_run_repository",
    "as_score_distribution_metric_repository",
]
