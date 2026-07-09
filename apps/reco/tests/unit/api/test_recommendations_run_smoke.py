"""API-INT-002 endpoint layer smoke tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from reco.application.recommendation_orchestrator.errors import RecoError
from reco.application.recommendation_orchestrator.orchestrator import OrchestratorOutcome
from conftest import (
    api_headers,
    build_domain_request,
    build_execution_context,
    sample_request_body,
    stub_api_client,
)


def test_run_recommendation_zero_items_completed(api_client: TestClient) -> None:
    response = api_client.post(
        "/internal/reco/v1/recommendations/run",
        json=sample_request_body(),
        headers=api_headers(),
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
    response = api_client.post(
        "/internal/reco/v1/recommendations/run",
        json=sample_request_body(),
        headers=api_headers(include_api_key=False),
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "GRS-AUTH-004"


def test_run_recommendation_invalid_api_key(api_client: TestClient) -> None:
    response = api_client.post(
        "/internal/reco/v1/recommendations/run",
        json=sample_request_body(),
        headers=api_headers(api_key="wrong-key"),
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "GRS-AUTH-001"


def test_run_recommendation_orchestrator_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RECO_INTERNAL_API_KEY", "test-internal-key")
    error_outcome = OrchestratorOutcome(
        success=False,
        reco_error=RecoError(error_code="GRS-REC-101", message="timeout"),
        execution_context=build_execution_context(request=build_domain_request()),
    )
    with stub_api_client(error_outcome) as client:
        response = client.post(
            "/internal/reco/v1/recommendations/run",
            json=sample_request_body(),
            headers=api_headers(),
        )
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "GRS-REC-101"
