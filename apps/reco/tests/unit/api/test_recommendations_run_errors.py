"""Error mapper unit tests for API-INT-002 endpoint layer."""

from __future__ import annotations

import pytest

from reco.application.recommendation_orchestrator.errors import RecoError
from reco.application.recommendation_orchestrator.orchestrator import OrchestratorOutcome
from reco.domain.recommendation.result import RecommendationResult, ResultStatus

from conftest import (
    api_headers,
    build_domain_request,
    build_execution_context,
    build_success_outcome,
    sample_request_body,
    stub_api_client,
)


@pytest.mark.parametrize(
    ("error_code", "expected_status"),
    [
        ("GRS-REC-002", 500),
        ("GRS-REC-201", 409),
        ("GRS-DB-001", 503),
        ("GRS-DB-002", 503),
        ("GRS-DB-005", 409),
        ("GRS-LLM-101", 504),
        ("GRS-LLM-102", 502),
        ("GRS-COM-003", 503),
    ],
)
def test_run_recommendation_orchestrator_error_maps_http_status(
    error_code: str,
    expected_status: int,
) -> None:
    error_outcome = OrchestratorOutcome(
        success=False,
        reco_error=RecoError(error_code=error_code, message="mapped error"),
        execution_context=build_execution_context(request=build_domain_request()),
    )
    with stub_api_client(error_outcome) as client:
        response = client.post(
            "/internal/reco/v1/recommendations/run",
            json=sample_request_body(),
            headers=api_headers(),
        )
    assert response.status_code == expected_status
    payload = response.json()
    assert payload["error"]["code"] == error_code
    assert "stack" not in payload["error"]["message"].lower()
    assert payload["meta"]["traceId"] == "550e8400-e29b-41d4-a716-446655440000"


def test_run_recommendation_orchestrator_success_without_result_returns_500() -> None:
    outcome = OrchestratorOutcome(
        success=True,
        recommendation_result=None,
        execution_context=build_execution_context(request=build_domain_request()),
    )
    with stub_api_client(outcome) as client:
        response = client.post(
            "/internal/reco/v1/recommendations/run",
            json=sample_request_body(),
            headers=api_headers(),
        )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "GRS-REC-999"


def test_run_recommendation_orchestrator_success_without_execution_context_returns_500() -> None:
    outcome = OrchestratorOutcome(
        success=True,
        recommendation_result=RecommendationResult(
            run_id="run_001",
            request_id="request_001",
            items=(),
            result_status=ResultStatus.COMPLETED,
        ),
        execution_context=None,
    )
    with stub_api_client(outcome) as client:
        response = client.post(
            "/internal/reco/v1/recommendations/run",
            json=sample_request_body(),
            headers=api_headers(),
        )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "GRS-REC-999"


def test_run_recommendation_orchestrator_failure_without_reco_error_returns_500() -> None:
    outcome = OrchestratorOutcome(
        success=False,
        reco_error=None,
        execution_context=build_execution_context(request=build_domain_request()),
    )
    with stub_api_client(outcome) as client:
        response = client.post(
            "/internal/reco/v1/recommendations/run",
            json=sample_request_body(),
            headers=api_headers(),
        )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "GRS-REC-999"


def test_run_recommendation_success_does_not_expose_internal_error_fields() -> None:
    outcome = build_success_outcome(items=())
    with stub_api_client(outcome) as client:
        response = client.post(
            "/internal/reco/v1/recommendations/run",
            json=sample_request_body(),
            headers=api_headers(),
        )
    assert response.status_code == 200
    assert "error" not in response.json()
