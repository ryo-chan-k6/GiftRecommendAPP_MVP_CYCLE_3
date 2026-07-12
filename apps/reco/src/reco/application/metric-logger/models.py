"""MOD-RECO-025 persistence models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MetricRecord:
    """Run-scoped Metric row for MVP InMemory persistence."""

    recommendation_run_id: str
    trace_id: str
    recommendation_latency_ms: int
    pre_filter_candidate_count: int | None
    retrieval_candidate_count: int | None
    post_filter_candidate_count: int | None
    final_result_count: int
    recommendation_empty: bool
    reason_fallback_count: int
    retrieval_phase_latency_ms: int | None
    matching_latency_ms: int | None
    ranking_latency_ms: int | None
    reason_generation_latency_ms: int | None
    recorded_at: datetime
    metric_source: str
