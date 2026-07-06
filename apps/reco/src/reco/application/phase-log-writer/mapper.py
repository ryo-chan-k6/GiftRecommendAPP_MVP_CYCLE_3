"""ExecutionContext to phase_log mapping (MOD-RECO-028 §9 / §16.1.1)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from .constants import OWNER_TYPE_RECOMMENDATION_RUN
from .models import BufferedPhaseEvent, PhaseLogRecord

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


def build_in_memory_event(
    context: ExecutionContext,
    *,
    phase_name: str,
    phase_status: str,
    module_id: str | None,
    error_code: str | None,
    duration_ms: int | None,
) -> dict[str, object]:
    return {
        "phase_name": phase_name,
        "phase_status": phase_status,
        "module_id": module_id,
        "error_code": error_code,
        "duration_ms": duration_ms,
        "trace_id": context.trace_id,
        "run_id": context.run_id,
    }


def build_started_record(
    context: ExecutionContext,
    *,
    phase_name: str,
    owner_id: str,
    started_at: datetime | None = None,
) -> PhaseLogRecord:
    timestamp = started_at or datetime.now(UTC)
    return PhaseLogRecord(
        trace_id=context.trace_id,
        owner_type=OWNER_TYPE_RECOMMENDATION_RUN,
        owner_id=owner_id,
        phase_name=phase_name,
        phase_status="started",
        started_at=timestamp,
    )


def build_terminal_detail_json(
    context: ExecutionContext,
    *,
    module_id: str | None,
) -> dict[str, object]:
    """Allowlist-only detail_json for terminal UPDATE (§16.1.1)."""
    detail: dict[str, object] = {}
    if module_id:
        detail["source_module_id"] = module_id

    allowlist_fields: tuple[tuple[str, object | None], ...] = (
        ("pre_filter_candidate_count", context.pre_filter_candidate_count),
        ("retrieval_candidate_count", context.retrieval_candidate_count),
        ("post_filter_candidate_count", context.post_filter_candidate_count),
        ("pre_hard_filter_latency_ms", context.pre_hard_filter_latency_ms),
        ("retrieval_latency_ms", context.retrieval_latency_ms),
        ("post_hard_filter_latency_ms", context.post_hard_filter_latency_ms),
        ("feature_matcher_latency_ms", context.feature_matcher_latency_ms),
        ("meaning_match_aggregator_latency_ms", context.meaning_match_aggregator_latency_ms),
        ("context_scorer_latency_ms", context.context_scorer_latency_ms),
        ("popularity_scorer_latency_ms", context.popularity_scorer_latency_ms),
        ("risk_scorer_latency_ms", context.risk_scorer_latency_ms),
        ("final_score_calculator_latency_ms", context.final_score_calculator_latency_ms),
        ("final_ranker_latency_ms", context.final_ranker_latency_ms),
        ("result_builder_latency_ms", context.result_builder_latency_ms),
        ("snapshot_builder_latency_ms", context.snapshot_builder_latency_ms),
        ("reason_generation_latency_ms", context.reason_generation_latency_ms),
    )
    for key, value in allowlist_fields:
        if value is not None:
            detail[key] = value

    if context.recommendation_result is not None:
        detail["final_result_count"] = context.recommendation_result.item_count

    return detail


def buffered_event_to_kwargs(event: BufferedPhaseEvent) -> dict[str, object]:
    return {
        "phase_name": event.phase_name,
        "phase_status": event.phase_status,
        "module_id": event.module_id,
        "error_code": event.error_code,
        "duration_ms": event.duration_ms,
    }
