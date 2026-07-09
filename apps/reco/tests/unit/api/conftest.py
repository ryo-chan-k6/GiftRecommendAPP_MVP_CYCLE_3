"""Test bootstrap and shared fixtures for API-INT-002 endpoint layer tests."""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_TEST_INTERNAL_API_KEY = "test-internal-key"
_DEFAULT_TRACE_ID = "550e8400-e29b-41d4-a716-446655440000"
_DEFAULT_REQUEST_ID = "req_01HZYX"
_DEFAULT_REQUEST_BODY_ID = "request_001"


def _load_package(import_root: str, init_relative: str) -> None:
    init_path = _ROOT / init_relative
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
    "reco.application.recommendation_orchestrator",
    "src/reco/application/recommendation-orchestrator/__init__.py",
)

from fastapi.testclient import TestClient

from reco.api.dependencies import get_orchestrator
from reco.api.main import create_app
from reco.application.recommendation_orchestrator.execution_context import ExecutionContext
from reco.application.recommendation_orchestrator.orchestrator import OrchestratorOutcome
from reco.domain.recommendation.inputs import ExecutionCondition, ExecutionMode
from reco.domain.recommendation.request import RecommendationRequest
from reco.domain.recommendation.result import (
    ReasonStatus,
    RecommendationResult,
    RecommendationResultItem,
    ResultStatus,
)


@dataclass
class StubOrchestrator:
    """Orchestrator stub for dependency_overrides."""

    outcome: OrchestratorOutcome

    def run(
        self,
        recommendation_request: RecommendationRequest,
        *,
        trace_id: str,
        execution_mode=None,
        caller_context=None,
    ) -> OrchestratorOutcome:
        _ = recommendation_request, trace_id, execution_mode, caller_context
        return self.outcome


def sample_request_body(
    *,
    request_id: str = _DEFAULT_REQUEST_BODY_ID,
    mode: str = "ui",
    top_k: int = 10,
    include_reason: bool | None = None,
    include_debug_info: bool | None = None,
) -> dict[str, object]:
    execution: dict[str, object] = {"mode": mode, "topK": top_k, "candidateLimit": 50}
    if include_reason is not None:
        execution["includeReason"] = include_reason
    if include_debug_info is not None:
        execution["includeDebugInfo"] = include_debug_info
    return {
        "recommendationRequestId": request_id,
        "recommendationRequest": {
            "relationship": {"relationshipCode": "boss", "relationshipLabel": "上司"},
            "occasion": {"occasionCode": "thanks", "occasionLabel": "お礼"},
            "execution": execution,
        },
    }


def api_headers(
    *,
    api_key: str = _TEST_INTERNAL_API_KEY,
    trace_id: str = _DEFAULT_TRACE_ID,
    request_id: str = _DEFAULT_REQUEST_ID,
    content_type: str = "application/json",
    accept: str = "application/json",
    include_api_key: bool = True,
) -> dict[str, str]:
    headers = {
        "X-Trace-Id": trace_id,
        "X-Request-Id": request_id,
        "Content-Type": content_type,
        "Accept": accept,
    }
    if include_api_key:
        headers["X-Internal-Api-Key"] = api_key
    return headers


def build_domain_request(
    *,
    request_id: str = _DEFAULT_REQUEST_BODY_ID,
    mode: ExecutionMode = ExecutionMode.UI,
    top_k: int = 10,
    include_reason: bool | None = None,
    include_debug_info: bool | None = None,
    eval_case_id: str | None = None,
    config_name: str | None = None,
    version_label: str | None = None,
    model_version_id: str | None = None,
) -> RecommendationRequest:
    return RecommendationRequest(
        request_id=request_id,
        execution=ExecutionCondition(
            mode=mode,
            top_k=top_k,
            include_reason=include_reason,
            include_debug_info=include_debug_info,
            eval_case_id=eval_case_id,
            config_name=config_name,
            version_label=version_label,
            model_version_id=model_version_id,
        ),
    )


def build_execution_context(
    *,
    request: RecommendationRequest | None = None,
    trace_id: str = _DEFAULT_TRACE_ID,
    retrieval_candidate_count: int | None = None,
    feature_matcher_candidate_count: int | None = None,
    final_ranker_selected_count: int | None = None,
    retrieval_latency_ms: int | None = None,
    feature_matcher_latency_ms: int | None = None,
    final_ranker_latency_ms: int | None = None,
    reason_generation_latency_ms: int | None = None,
    reason_fallback_count: int = 0,
    config_versions: dict[str, str] | None = None,
) -> ExecutionContext:
    domain_request = request or build_domain_request()
    return ExecutionContext(
        recommendation_request=domain_request,
        trace_id=trace_id,
        execution_mode=domain_request.execution.mode if domain_request.execution else ExecutionMode.UI,
        retrieval_candidate_count=retrieval_candidate_count,
        feature_matcher_candidate_count=feature_matcher_candidate_count,
        final_ranker_selected_count=final_ranker_selected_count,
        retrieval_latency_ms=retrieval_latency_ms,
        feature_matcher_latency_ms=feature_matcher_latency_ms,
        final_ranker_latency_ms=final_ranker_latency_ms,
        reason_generation_latency_ms=reason_generation_latency_ms,
        reason_fallback_count=reason_fallback_count,
        config_versions=config_versions or {},
    )


def build_result_item(
    *,
    item_id: str = "item_001",
    rank: int = 1,
    final_score: float = 0.82,
    reason_summary: str | None = "上司へのお礼として候補にしています。",
    reason_status: ReasonStatus | None = ReasonStatus.COMPLETED,
    is_fallback: bool = False,
) -> RecommendationResultItem:
    return RecommendationResultItem(
        item_id=item_id,
        rank=rank,
        final_score=final_score,
        reason_summary=reason_summary,
        reason_status=reason_status,
        is_fallback=is_fallback,
    )


def build_success_outcome(
    *,
    items: tuple[RecommendationResultItem, ...] = (),
    result_status: ResultStatus = ResultStatus.COMPLETED,
    context: ExecutionContext | None = None,
    version_info: dict[str, str] | None = None,
    run_id: str = "run_001",
    request_id: str = _DEFAULT_REQUEST_BODY_ID,
) -> OrchestratorOutcome:
    execution_context = context or build_execution_context()
    result = RecommendationResult(
        run_id=run_id,
        request_id=request_id,
        items=items,
        result_status=result_status,
        version_info=version_info,
    )
    return OrchestratorOutcome(
        success=True,
        recommendation_result=result,
        execution_context=execution_context,
    )


@contextmanager
def stub_api_client(
    outcome: OrchestratorOutcome,
    *,
    configure_env: bool = True,
    api_key_env: str = _TEST_INTERNAL_API_KEY,
) -> Iterator[TestClient]:
    """TestClient with Orchestrator stub; clears dependency_overrides on exit."""
    import os

    previous = os.environ.get("RECO_INTERNAL_API_KEY")
    if configure_env:
        os.environ["RECO_INTERNAL_API_KEY"] = api_key_env
    app = create_app()
    app.dependency_overrides[get_orchestrator] = lambda: StubOrchestrator(outcome)
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        if configure_env:
            if previous is None:
                os.environ.pop("RECO_INTERNAL_API_KEY", None)
            else:
                os.environ["RECO_INTERNAL_API_KEY"] = previous


@pytest.fixture
def api_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Default client: empty completed result (smoke-compatible)."""
    monkeypatch.setenv("RECO_INTERNAL_API_KEY", _TEST_INTERNAL_API_KEY)
    outcome = build_success_outcome(
        items=(),
        result_status=ResultStatus.EMPTY,
        version_info={"recommendation_result_id": "result_002"},
        run_id="run_002",
        context=build_execution_context(),
    )
    app = create_app()
    app.dependency_overrides[get_orchestrator] = lambda: StubOrchestrator(outcome)
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def score_breakdown_version_info(item_id: str, breakdown: dict[str, object]) -> dict[str, str]:
    return {f"item:{item_id}:score_breakdown_json": json.dumps(breakdown)}
