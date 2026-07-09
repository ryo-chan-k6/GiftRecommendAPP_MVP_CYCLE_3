"""API-INT-002 endpoint layer smoke tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from reco.api.dependencies import get_orchestrator
from reco.api.main import create_app
from reco.application.recommendation_orchestrator.errors import RecoError
from reco.application.recommendation_orchestrator.execution_context import ExecutionContext
from reco.application.recommendation_orchestrator.orchestrator import OrchestratorOutcome
from reco.domain.recommendation.inputs import ExecutionCondition, ExecutionMode
from reco.domain.recommendation.request import RecommendationRequest
from reco.domain.recommendation.result import RecommendationResult, ResultStatus


@dataclass
class _StubOrchestrator:
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


def _sample_request_body() -> dict[str, object]:
    return {
        "recommendationRequestId": "request_001",
        "recommendationRequest": {
            "relationship": {"relationshipCode": "boss", "relationshipLabel": "上司"},
            "occasion": {"occasionCode": "thanks", "occasionLabel": "お礼"},
            "execution": {"mode": "ui", "topK": 10, "candidateLimit": 50},
        },
    }


def _headers(*, api_key: str = "test-internal-key") -> dict[str, str]:
    return {
        "X-Internal-Api-Key": api_key,
        "X-Trace-Id": "550e8400-e29b-41d4-a716-446655440000",
        "X-Request-Id": "req_01HZYX",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


@pytest.fixture
def api_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("RECO_INTERNAL_API_KEY", "test-internal-key")
    empty_outcome = OrchestratorOutcome(
        success=True,
        recommendation_result=RecommendationResult(
            run_id="run_002",
            request_id="request_001",
            items=(),
            result_status=ResultStatus.EMPTY,
            version_info={"recommendation_result_id": "result_002"},
        ),
        execution_context=ExecutionContext(
            recommendation_request=RecommendationRequest(
                request_id="request_001",
                execution=ExecutionCondition(mode=ExecutionMode.UI, top_k=10),
            ),
            trace_id="550e8400-e29b-41d4-a716-446655440000",
            execution_mode=ExecutionMode.UI,
        ),
    )
    app = create_app()
    app.dependency_overrides[get_orchestrator] = lambda: _StubOrchestrator(empty_outcome)
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_run_recommendation_zero_items_completed(api_client: TestClient) -> None:
    response = api_client.post(
        "/internal/reco/v1/recommendations/run",
        json=_sample_request_body(),
        headers=_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["resultStatus"] == "completed"
    assert payload["data"]["resultItemCount"] == 0
    assert payload["data"]["resultItems"] == []
    assert payload["meta"]["traceId"] == "550e8400-e29b-41d4-a716-446655440000"
    assert payload["meta"]["requestId"] == "req_01HZYX"
    assert payload["meta"]["resultCode"] == "GRS-REC-001"


def test_run_recommendation_missing_api_key(api_client: TestClient) -> None:
    headers = _headers()
    del headers["X-Internal-Api-Key"]
    response = api_client.post(
        "/internal/reco/v1/recommendations/run",
        json=_sample_request_body(),
        headers=headers,
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "GRS-AUTH-004"


def test_run_recommendation_invalid_api_key(api_client: TestClient) -> None:
    response = api_client.post(
        "/internal/reco/v1/recommendations/run",
        json=_sample_request_body(),
        headers=_headers(api_key="wrong-key"),
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "GRS-AUTH-001"


def test_run_recommendation_orchestrator_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RECO_INTERNAL_API_KEY", "test-internal-key")
    error_outcome = OrchestratorOutcome(
        success=False,
        reco_error=RecoError(error_code="GRS-REC-101", message="timeout"),
        execution_context=ExecutionContext(
            recommendation_request=RecommendationRequest(
                request_id="request_001",
                execution=ExecutionCondition(mode=ExecutionMode.UI),
            ),
            trace_id="550e8400-e29b-41d4-a716-446655440000",
            execution_mode=ExecutionMode.UI,
        ),
    )
    app = create_app()
    app.dependency_overrides[get_orchestrator] = lambda: _StubOrchestrator(error_outcome)
    with TestClient(app) as client:
        response = client.post(
            "/internal/reco/v1/recommendations/run",
            json=_sample_request_body(),
            headers=_headers(),
        )
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "GRS-REC-101"
