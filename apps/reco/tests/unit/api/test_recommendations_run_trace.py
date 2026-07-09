"""Trace propagation unit tests for API-INT-002 (契約仕様書 §12 No.6)."""

from __future__ import annotations

from conftest import api_headers, build_result_item, build_success_outcome, sample_request_body, stub_api_client


def test_run_recommendation_trace_propagated_on_success() -> None:
    trace_id = "trace-success-001"
    request_id = "req-success-001"
    outcome = build_success_outcome(
        items=(build_result_item(item_id="item_001", final_score=0.82),),
        version_info={
            "recommendation_result_id": "result_001",
            "item:item_001:item_name_snapshot": "上品な焼き菓子ギフトセット",
        },
    )
    with stub_api_client(outcome) as client:
        response = client.post(
            "/internal/reco/v1/recommendations/run",
            json=sample_request_body(),
            headers=api_headers(trace_id=trace_id, request_id=request_id),
        )
    assert response.status_code == 200
    meta = response.json()["meta"]
    assert meta["traceId"] == trace_id
    assert meta["requestId"] == request_id
    assert meta.get("resultCode") is None


def test_run_recommendation_trace_propagated_on_validation_error(api_client) -> None:
    trace_id = "trace-validation-001"
    request_id = "req-validation-001"
    response = api_client.post(
        "/internal/reco/v1/recommendations/run",
        json={},
        headers=api_headers(trace_id=trace_id, request_id=request_id),
    )
    assert response.status_code == 400
    meta = response.json()["meta"]
    assert meta["traceId"] == trace_id
    assert meta["requestId"] == request_id


def test_run_recommendation_trace_propagated_on_auth_error(api_client) -> None:
    trace_id = "trace-auth-001"
    request_id = "req-auth-001"
    response = api_client.post(
        "/internal/reco/v1/recommendations/run",
        json=sample_request_body(),
        headers=api_headers(
            trace_id=trace_id,
            request_id=request_id,
            include_api_key=False,
        ),
    )
    assert response.status_code == 401
    meta = response.json()["meta"]
    assert meta["traceId"] == trace_id
    assert meta["requestId"] == request_id
