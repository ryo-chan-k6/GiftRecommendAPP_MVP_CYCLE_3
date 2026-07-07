"""Shared fixtures for MOD-RECO-025 smoke tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)
from reco.domain import (
    ExecutionMode,
    RecommendationRequest,
    RecommendationResult,
    RecommendationResultItem,
    RecommendationRun,
    RunStatus,
)


def _load_package(import_root: str, relative_path: str) -> None:
    init_path = Path(__file__).resolve().parents[4] / relative_path / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        import_root,
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load package: {import_root}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_load_package(
    "reco.application.metric_logger",
    "src/reco/application/metric-logger",
)

from reco.application.metric_logger import (  # noqa: E402
    InMemoryMetricLoggerRepository,
    MetricLogger,
)

DEFAULT_RUN_ID = "run-metric-logger-1"
DEFAULT_REQUEST_ID = "req-metric-logger-1"
DEFAULT_TRACE_ID = "trace-metric-logger-1"

STUB_COMPATIBLE_KEYS = frozenset(
    {
        "recommendation_latency_ms",
        "reason_fallback_count",
        "final_result_count",
        "trace_id",
        "run_id",
    }
)

TIER_1_KEYS = frozenset(
    {
        "recommendation_run_id",
        "trace_id",
        "run_id",
        "recommendation_latency_ms",
        "pre_filter_candidate_count",
        "retrieval_candidate_count",
        "post_filter_candidate_count",
        "final_result_count",
        "recommendation_empty",
        "reason_fallback_count",
        "recorded_at",
        "metric_source",
    }
)

TIER_1B_KEYS = frozenset(
    {
        "retrieval_phase_latency_ms",
        "matching_latency_ms",
        "ranking_latency_ms",
        "reason_generation_latency_ms",
    }
)


def build_logger(
    repository: InMemoryMetricLoggerRepository | None = None,
) -> tuple[MetricLogger, InMemoryMetricLoggerRepository]:
    repo = repository or InMemoryMetricLoggerRepository()
    return MetricLogger(repository=repo), repo


def sample_context(*, include_run: bool = True) -> ExecutionContext:
    recommendation_run = None
    if include_run:
        recommendation_run = RecommendationRun(
            run_id=DEFAULT_RUN_ID,
            request_id=DEFAULT_REQUEST_ID,
            status=RunStatus.SUCCEEDED,
        )
    return ExecutionContext(
        recommendation_request=RecommendationRequest(request_id=DEFAULT_REQUEST_ID),
        trace_id=DEFAULT_TRACE_ID,
        execution_mode=ExecutionMode.UI,
        recommendation_run=recommendation_run,
    )


def sample_rich_context(*, include_run: bool = True) -> ExecutionContext:
    context = sample_context(include_run=include_run)
    context.pre_filter_candidate_count = 42
    context.retrieval_candidate_count = 30
    context.post_filter_candidate_count = 18
    context.reason_fallback_count = 2
    context.pre_hard_filter_latency_ms = 11
    context.retrieval_latency_ms = 22
    context.feature_matcher_latency_ms = 30
    context.meaning_match_aggregator_latency_ms = 20
    context.context_scorer_latency_ms = 10
    context.popularity_scorer_latency_ms = 15
    context.risk_scorer_latency_ms = 12
    context.final_score_calculator_latency_ms = 18
    context.final_ranker_latency_ms = 25
    context.reason_generation_latency_ms = 40
    context.recommendation_result = RecommendationResult(
        run_id=DEFAULT_RUN_ID,
        request_id=DEFAULT_REQUEST_ID,
        items=(
            RecommendationResultItem(item_id="item-1", rank=1),
            RecommendationResultItem(item_id="item-2", rank=2),
        ),
    )
    return context
