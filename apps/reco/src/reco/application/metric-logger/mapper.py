"""ExecutionContext to MetricRecord mapping."""

from __future__ import annotations

from datetime import UTC, datetime

from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)

from .constants import METRIC_SOURCE
from .models import MetricRecord


def sum_present_latencies(*values: int | None) -> int | None:
    """Sum latency fields; return None when all inputs are None."""
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present)


def resolve_final_result_count(context: ExecutionContext) -> int:
    if context.recommendation_result is not None:
        return context.recommendation_result.item_count
    if context.result_builder_item_count is not None:
        return context.result_builder_item_count
    return 0


def resolve_retrieval_phase_latency_ms(context: ExecutionContext) -> int | None:
    return sum_present_latencies(
        context.pre_hard_filter_latency_ms,
        context.retrieval_latency_ms,
    )


def resolve_matching_latency_ms(context: ExecutionContext) -> int | None:
    return sum_present_latencies(
        context.feature_matcher_latency_ms,
        context.meaning_match_aggregator_latency_ms,
        context.context_scorer_latency_ms,
    )


def resolve_ranking_latency_ms(context: ExecutionContext) -> int | None:
    return sum_present_latencies(
        context.popularity_scorer_latency_ms,
        context.risk_scorer_latency_ms,
        context.final_score_calculator_latency_ms,
        context.final_ranker_latency_ms,
    )


def build_metric_record(
    context: ExecutionContext,
    *,
    recorded_at: datetime | None = None,
) -> MetricRecord:
    run_id = context.run_id
    if run_id is None:
        raise ValueError("run_id is required to build MetricRecord")

    final_result_count = resolve_final_result_count(context)
    timestamp = recorded_at or datetime.now(UTC)

    return MetricRecord(
        recommendation_run_id=run_id,
        trace_id=context.trace_id,
        recommendation_latency_ms=context.recommendation_latency_ms,
        pre_filter_candidate_count=context.pre_filter_candidate_count,
        retrieval_candidate_count=context.retrieval_candidate_count,
        post_filter_candidate_count=context.post_filter_candidate_count,
        final_result_count=final_result_count,
        recommendation_empty=final_result_count == 0,
        reason_fallback_count=context.reason_fallback_count,
        retrieval_phase_latency_ms=resolve_retrieval_phase_latency_ms(context),
        matching_latency_ms=resolve_matching_latency_ms(context),
        ranking_latency_ms=resolve_ranking_latency_ms(context),
        reason_generation_latency_ms=context.reason_generation_latency_ms,
        recorded_at=timestamp,
        metric_source=METRIC_SOURCE,
    )


def metric_record_to_observation_dict(record: MetricRecord) -> dict[str, object]:
    """Build StubMetricLogger-compatible observation payload with Tier 1 / 1b fields."""
    return {
        "recommendation_run_id": record.recommendation_run_id,
        "trace_id": record.trace_id,
        "run_id": record.recommendation_run_id,
        "recommendation_latency_ms": record.recommendation_latency_ms,
        "pre_filter_candidate_count": record.pre_filter_candidate_count,
        "retrieval_candidate_count": record.retrieval_candidate_count,
        "post_filter_candidate_count": record.post_filter_candidate_count,
        "final_result_count": record.final_result_count,
        "recommendation_empty": record.recommendation_empty,
        "reason_fallback_count": record.reason_fallback_count,
        "retrieval_phase_latency_ms": record.retrieval_phase_latency_ms,
        "matching_latency_ms": record.matching_latency_ms,
        "ranking_latency_ms": record.ranking_latency_ms,
        "reason_generation_latency_ms": record.reason_generation_latency_ms,
        "recorded_at": record.recorded_at,
        "metric_source": record.metric_source,
    }
