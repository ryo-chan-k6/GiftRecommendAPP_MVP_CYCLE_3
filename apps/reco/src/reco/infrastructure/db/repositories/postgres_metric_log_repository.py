"""PostgreSQL MetricLoggerRepository Tier 1 (MOD-RECO-025 → metric_log)."""

from __future__ import annotations

from dataclasses import dataclass

from reco.infrastructure.db.application_bootstrap import ensure_observability_application_packages
from reco.infrastructure.db.session import DatabaseSession

ensure_observability_application_packages()
from reco.application.metric_logger.models import MetricRecord
from reco.application.metric_logger.ports import MetricLoggerRepository

_INSERT_SQL = """
INSERT INTO metric_log (
  trace_id,
  recommendation_run_id,
  recommendation_latency_ms,
  pre_filter_candidate_count,
  retrieval_candidate_count,
  post_filter_candidate_count,
  final_result_count,
  recommendation_empty,
  reason_fallback_count,
  retrieval_phase_latency_ms,
  matching_latency_ms,
  ranking_latency_ms,
  reason_generation_latency_ms,
  recorded_at,
  metric_source
) VALUES (
  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""


@dataclass
class PostgresMetricLogRepository:
    """PostgreSQL Tier 1 repository for ``metric_log``."""

    session: DatabaseSession

    def save(self, record: MetricRecord) -> None:
        affected = self.session.execute(
            _INSERT_SQL,
            (
                record.trace_id,
                record.recommendation_run_id,
                record.recommendation_latency_ms,
                record.pre_filter_candidate_count,
                record.retrieval_candidate_count,
                record.post_filter_candidate_count,
                record.final_result_count,
                record.recommendation_empty,
                record.reason_fallback_count,
                record.retrieval_phase_latency_ms,
                record.matching_latency_ms,
                record.ranking_latency_ms,
                record.reason_generation_latency_ms,
                record.recorded_at,
                record.metric_source,
            ),
        )
        if affected != 1:
            raise RuntimeError("metric_log save failed")


def as_metric_logger_repository(
    repository: PostgresMetricLogRepository,
) -> MetricLoggerRepository:
    """Narrow a concrete repository to the Protocol type."""

    return repository
