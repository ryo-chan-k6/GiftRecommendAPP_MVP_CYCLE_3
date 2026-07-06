"""Shared fixtures for MOD-RECO-028 smoke tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)
from reco.application.recommendation_orchestrator.ports import PhaseStatus
from reco.domain import ExecutionMode, RecommendationRequest, RecommendationRun, RunStatus


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
) -> None:
    writer.record_phase(
        context,
        phase_name=phase_name,
        phase_status=PhaseStatus.SUCCEEDED,
        duration_ms=duration_ms,
    )
