"""Test bootstrap and shared fixtures for MOD-RECO-024 smoke tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)
from reco.domain import ExecutionMode, RecommendationRequest, RecommendationRun, RunStatus
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


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
    "reco.application.candidate_retriever",
    "src/reco/application/candidate-retriever",
)
_load_package(
    "reco.application.error_log_writer",
    "src/reco/application/error-log-writer",
)

from reco.application.candidate_retriever.errors import (  # noqa: E402
    PreHardFilterError,
    RetrievalError,
)
from reco.application.error_log_writer import (  # noqa: E402
    ErrorLogWriter,
    InMemoryErrorLogRepository,
)
from reco.application.reco_error_handler import (  # noqa: E402
    ErrorLogWriteRequest,
    RecoErrorHandler,
    build_default_reco_error_handler,
)
from reco.application.reco_error_handler.executor import NoOpErrorLogWriter  # noqa: E402
from reco.application.recommendation_orchestrator.errors import RecoError  # noqa: E402

DEFAULT_RUN_ID = "run-reco-error-handler-1"
DEFAULT_REQUEST_ID = "req-reco-error-handler-1"
DEFAULT_TRACE_ID = "trace-reco-error-handler-1"


def _sample_context(*, include_run: bool = True) -> ExecutionContext:
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


def build_error_handler(
    *,
    error_log_writer: NoOpErrorLogWriter | ErrorLogWriter | None = None,
) -> RecoErrorHandler:
    writer = error_log_writer or NoOpErrorLogWriter()
    return RecoErrorHandler(
        error_log_writer=writer,
        logger=ScaffoldRecoLogger(),
    )


def build_error_handler_with_writer(
    repository: InMemoryErrorLogRepository | None = None,
) -> tuple[RecoErrorHandler, InMemoryErrorLogRepository]:
    repo = repository or InMemoryErrorLogRepository()
    writer = ErrorLogWriter(repository=repo)
    handler = RecoErrorHandler(
        error_log_writer=writer,
        logger=ScaffoldRecoLogger(),
        append_test_seam_events=False,
    )
    return handler, repo
