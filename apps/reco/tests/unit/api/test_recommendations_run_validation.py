"""Validation and auth unit tests for API-INT-002 (契約仕様書 §12 No.3, 4, 5)."""

from __future__ import annotations

import pytest

from reco.application.recommendation_orchestrator.errors import RecoError
from reco.application.recommendation_orchestrator.orchestrator import OrchestratorOutcome

from conftest import (
    api_headers,
    build_domain_request,
    build_execution_context,
    sample_request_body,
    stub_api_client,
)


@pytest.mark.parametrize(
    ("body", "expected_field_fragment"),
    [
        ({}, "recommendationRequestId"),
        (
            {
                "recommendationRequest": {
                    "relationship": {"relationshipCode": "boss"},
                    "occasion": {"occasionCode": "thanks"},
                    "execution": {"mode": "ui"},
                },
            },
            "recommendationRequestId",
        ),
    ],
)
def test_run_recommendation_missing_request_id_returns_400(
    api_client,
    body: dict[str, object],
    expected_field_fragment: str,
) -> None:
    response = api_client.post(
        "/internal/reco/v1/recommendations/run",
        json=body,
        headers=api_headers(),
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "GRS-REQ-001"
    assert payload["meta"]["traceId"] == "550e8400-e29b-41d4-a716-446655440000"
    details = payload["error"].get("details") or []
    assert any(expected_field_fragment in detail["field"] for detail in details)


@pytest.mark.parametrize(
    "header_name",
    ["X-Trace-Id", "X-Request-Id"],
)
def test_run_recommendation_missing_trace_headers_returns_400(
    api_client,
    header_name: str,
) -> None:
    headers = api_headers()
    del headers[header_name]
    response = api_client.post(
        "/internal/reco/v1/recommendations/run",
        json=sample_request_body(),
        headers=headers,
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "GRS-REQ-001"
    if header_name == "X-Trace-Id":
        assert payload["meta"]["traceId"] == ""
    else:
        assert payload["meta"]["requestId"] == ""


def test_run_recommendation_invalid_content_type_returns_400(api_client) -> None:
    response = api_client.post(
        "/internal/reco/v1/recommendations/run",
        json=sample_request_body(),
        headers=api_headers(content_type="text/plain"),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "GRS-REQ-001"


def test_run_recommendation_missing_internal_api_key_env_returns_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RECO_INTERNAL_API_KEY", raising=False)
    outcome = OrchestratorOutcome(
        success=False,
        reco_error=RecoError(error_code="GRS-REC-101", message="should not run"),
        execution_context=build_execution_context(request=build_domain_request()),
    )
    with stub_api_client(outcome, configure_env=False) as client:
        response = client.post(
            "/internal/reco/v1/recommendations/run",
            json=sample_request_body(),
            headers=api_headers(),
        )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "GRS-AUTH-004"


def test_run_recommendation_permission_error_maps_to_403() -> None:
    error_outcome = OrchestratorOutcome(
        success=False,
        reco_error=RecoError(error_code="GRS-AUTH-002", message="forbidden"),
        execution_context=build_execution_context(request=build_domain_request()),
    )
    with stub_api_client(error_outcome) as client:
        response = client.post(
            "/internal/reco/v1/recommendations/run",
            json=sample_request_body(),
            headers=api_headers(),
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "GRS-AUTH-002"
