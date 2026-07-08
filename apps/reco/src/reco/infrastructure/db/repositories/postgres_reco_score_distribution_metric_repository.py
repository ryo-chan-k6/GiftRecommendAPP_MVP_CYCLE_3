"""PostgreSQL ScoreDistributionMetricRepository Tier 2 (MOD-RECO-025)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from reco.infrastructure.db.session import DatabaseSession

ScoreType = Literal["context_score", "final_score"]


@dataclass(frozen=True)
class ScoreDistributionMetricRecord:
    """Run-scoped score distribution row for ``reco_score_distribution_metric``."""

    recommendation_run_id: str
    recommendation_result_id: str
    semantic_config_version_id: str
    ranking_config_id: str
    score_type: ScoreType
    sample_count: int
    mean: float
    calculated_at: datetime
    stddev: float | None = None
    min_value: float | None = None
    max_value: float | None = None
    p10: float | None = None
    p50: float | None = None
    p90: float | None = None
    near_zero_rate: float | None = None
    near_one_rate: float | None = None
    mid_concentration_rate: float | None = None
    nan_count: int = 0
    out_of_range_count: int = 0
    aggregation_key: str | None = None


class ScoreDistributionMetricRepository(Protocol):
    """Persistence boundary for Tier 2 distribution metrics."""

    def upsert(self, record: ScoreDistributionMetricRecord) -> None: ...


_UPSERT_SQL = """
INSERT INTO reco_score_distribution_metric (
  recommendation_run_id,
  recommendation_result_id,
  batch_run_id,
  semantic_config_version_id,
  ranking_config_id,
  score_type,
  aggregation_scope,
  aggregation_key,
  sample_count,
  mean,
  stddev,
  min_value,
  max_value,
  p10,
  p50,
  p90,
  near_zero_rate,
  near_one_rate,
  mid_concentration_rate,
  nan_count,
  out_of_range_count,
  calculated_at,
  updated_at
) VALUES (
  %s, %s, NULL, %s, %s, %s, 'run', %s,
  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
ON CONFLICT (
  recommendation_run_id,
  recommendation_result_id,
  score_type,
  aggregation_scope,
  aggregation_key
)
DO UPDATE SET
  sample_count = EXCLUDED.sample_count,
  mean = EXCLUDED.mean,
  stddev = EXCLUDED.stddev,
  min_value = EXCLUDED.min_value,
  max_value = EXCLUDED.max_value,
  p10 = EXCLUDED.p10,
  p50 = EXCLUDED.p50,
  p90 = EXCLUDED.p90,
  near_zero_rate = EXCLUDED.near_zero_rate,
  near_one_rate = EXCLUDED.near_one_rate,
  mid_concentration_rate = EXCLUDED.mid_concentration_rate,
  nan_count = EXCLUDED.nan_count,
  out_of_range_count = EXCLUDED.out_of_range_count,
  calculated_at = EXCLUDED.calculated_at,
  updated_at = EXCLUDED.updated_at
"""


@dataclass
class PostgresScoreDistributionMetricRepository:
    """PostgreSQL Tier 2 repository for ``reco_score_distribution_metric``."""

    session: DatabaseSession

    def upsert(self, record: ScoreDistributionMetricRecord) -> None:
        now = record.calculated_at
        affected = self.session.execute(
            _UPSERT_SQL,
            (
                record.recommendation_run_id,
                record.recommendation_result_id,
                record.semantic_config_version_id,
                record.ranking_config_id,
                record.score_type,
                record.aggregation_key,
                record.sample_count,
                record.mean,
                record.stddev,
                record.min_value,
                record.max_value,
                record.p10,
                record.p50,
                record.p90,
                record.near_zero_rate,
                record.near_one_rate,
                record.mid_concentration_rate,
                record.nan_count,
                record.out_of_range_count,
                record.calculated_at,
                now,
            ),
        )
        if affected != 1:
            raise RuntimeError("reco_score_distribution_metric upsert failed")


def as_score_distribution_metric_repository(
    repository: PostgresScoreDistributionMetricRepository,
) -> ScoreDistributionMetricRepository:
    """Narrow a concrete repository to the Protocol type."""

    return repository
