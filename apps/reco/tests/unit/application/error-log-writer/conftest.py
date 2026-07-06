"""Shared fixtures for MOD-RECO-029 smoke tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)
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
    "reco.application.reco_error_handler",
    "src/reco/application/reco-error-handler",
)
_load_package(
    "reco.application.error_log_writer",
    "src/reco/application/error-log-writer",
)

from reco.application.error_log_writer import (  # noqa: E402
    ErrorLogWriter,
    InMemoryErrorLogRepository,
)
from reco.application.reco_error_handler.executor import RecoErrorHandler  # noqa: E402
from reco.application.reco_error_handler.models import ErrorLogWriteRequest  # noqa: E402

DEFAULT_RUN_ID = "run-error-log-writer-1"
DEFAULT_REQUEST_ID = "req-error-log-writer-1"
DEFAULT_TRACE_ID = "trace-error-log-writer-1"


def sample_write_request(**overrides: object) -> ErrorLogWriteRequest:
    payload = {
        "trace_id": "trace-029-smoke",
        "owner_type": "recommendation_run",
        "owner_id": "550e8400-e29b-41d4-a716-446655440000",
        "service": "reco",
        "error_code": "GRS-REC-012",
        "error_message": "ranking failed",
        "severity": "error",
        "retryable": False,
        "request_id": "req-029-smoke",
        "error_detail_json": {
            "source_module_id": "MOD-RECO-017",
            "phase_name": "ranking",
            "detail_error_code": "GRS-DB-001",
        },
    }
    payload.update(overrides)
    return ErrorLogWriteRequest(**payload)  # type: ignore[arg-type]


def build_writer(
    repository: InMemoryErrorLogRepository | None = None,
) -> tuple[ErrorLogWriter, InMemoryErrorLogRepository]:
    repo = repository or InMemoryErrorLogRepository()
    return ErrorLogWriter(repository=repo), repo


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


def build_error_handler_with_writer(
    repository: InMemoryErrorLogRepository | None = None,
) -> tuple[RecoErrorHandler, InMemoryErrorLogRepository]:
    writer, repo = build_writer(repository=repository)
    handler = RecoErrorHandler(error_log_writer=writer, append_test_seam_events=False)
    return handler, repo
