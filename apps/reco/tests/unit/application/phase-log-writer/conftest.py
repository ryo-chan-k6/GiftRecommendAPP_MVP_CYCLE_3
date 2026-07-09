"""Shared fixtures for MOD-RECO-028 smoke tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)
from reco.application.recommendation_orchestrator.ports import PhaseStatus
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
    "reco.application.phase_log_writer",
    "src/reco/application/phase-log-writer",
)

from reco.application.phase_log_writer import (  # noqa: E402
    InMemoryPhaseLogRepository,
    PhaseLogWriter,
)

DEFAULT_RUN_ID = "run-phase-log-writer-1"
DEFAULT_REQUEST_ID = "req-phase-log-writer-1"
DEFAULT_TRACE_ID = "trace-phase-log-writer-1"

STUB_COMPATIBLE_EVENT_KEYS = frozenset(
    {
        "phase_name",
        "phase_status",
        "module_id",
        "error_code",
        "duration_ms",
        "trace_id",
        "run_id",
    }
)


def build_writer(
    repository: InMemoryPhaseLogRepository | None = None,
) -> tuple[PhaseLogWriter, InMemoryPhaseLogRepository]:
    repo = repository or InMemoryPhaseLogRepository()
    return PhaseLogWriter(repository=repo), repo


def sample_context(*, include_run: bool = True) -> ExecutionContext:
    recommendation_run = None
    if include_run:
        recommendation_run = RecommendationRun(
            run_id=DEFAULT_RUN_ID,
            request_id=DEFAULT_REQUEST_ID,
            status=RunStatus.RUNNING,
        )
    return ExecutionContext(
        recommendation_request=RecommendationRequest(request_id=DEFAULT_REQUEST_ID),
        trace_id=DEFAULT_TRACE_ID,
        execution_mode=ExecutionMode.UI,
        recommendation_run=recommendation_run,
    )


def record_started(
    writer: PhaseLogWriter,
    context: ExecutionContext,
    *,
    phase_name: str = "request_received",
) -> None:
    writer.record_phase(
        context,
        phase_name=phase_name,
        phase_status=PhaseStatus.STARTED,
    )


def record_succeeded(
    writer: PhaseLogWriter,
    context: ExecutionContext,
    *,
    phase_name: str = "request_received",
    duration_ms: int = 12,
    module_id: str | None = "MOD-RECO-001",
) -> None:
    writer.record_phase(
        context,
        phase_name=phase_name,
        phase_status=PhaseStatus.SUCCEEDED,
        module_id=module_id,
        duration_ms=duration_ms,
    )


def record_failed(
    writer: PhaseLogWriter,
    context: ExecutionContext,
    *,
    phase_name: str = "request_received",
    error_code: str = "GRS-REC-011",
    duration_ms: int = 15,
    module_id: str | None = "MOD-RECO-014",
) -> None:
    writer.record_phase(
        context,
        phase_name=phase_name,
        phase_status=PhaseStatus.FAILED,
        module_id=module_id,
        error_code=error_code,
        duration_ms=duration_ms,
    )


def sample_rich_context(*, include_run: bool = True) -> ExecutionContext:
    """Context with sensitive caller fields and allowlisted summary counters."""
    context = sample_context(include_run=include_run)
    context.caller_context = {
        "prompt": "full user prompt that must not appear in detail_json",
        "api_key": "sk-test-secret-key",
        "authorization": "Bearer test-token",
    }
    context.pre_filter_candidate_count = 42
    context.retrieval_candidate_count = 30
    context.post_filter_candidate_count = 18
    context.pre_hard_filter_latency_ms = 11
    context.recommendation_result = RecommendationResult(
        run_id=DEFAULT_RUN_ID,
        request_id=DEFAULT_REQUEST_ID,
        items=(RecommendationResultItem(item_id="item-1", rank=1),),
    )
    return context
