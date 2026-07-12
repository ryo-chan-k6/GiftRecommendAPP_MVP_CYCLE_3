"""API-INT-001 Reco health endpoint unit tests."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from reco.api.main import create_app
from reco.api.metrics.health_metrics import (
    get_health_metric_count,
    reset_health_metrics,
)

_TEST_INTERNAL_API_KEY = "test-internal-key"
_DEFAULT_TRACE_ID = "550e8400-e29b-41d4-a716-446655440000"
_DEFAULT_REQUEST_ID = "req_01HZYX"
_HEALTH_PATH = "/internal/reco/v1/health"


def _health_headers(
    *,
    api_key: str = _TEST_INTERNAL_API_KEY,
    include_api_key: bool = True,
    include_trace: bool = True,
) -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/json"}
    if include_api_key:
        headers["X-Internal-Api-Key"] = api_key
    if include_trace:
        headers["X-Trace-Id"] = _DEFAULT_TRACE_ID
        headers["X-Request-Id"] = _DEFAULT_REQUEST_ID
    return headers


@contextmanager
def health_client(*, configure_env: bool = True) -> Iterator[TestClient]:
    previous = os.environ.get("RECO_INTERNAL_API_KEY")
    previous_db = os.environ.get("DATABASE_URL")
    if configure_env:
        os.environ["RECO_INTERNAL_API_KEY"] = _TEST_INTERNAL_API_KEY
    # ローカル scaffold probe を使うため DATABASE_URL を外す
    os.environ.pop("DATABASE_URL", None)
    reset_health_metrics()
    app = create_app()
    try:
        with TestClient(app) as client:
            yield client
    finally:
        if configure_env:
            if previous is None:
                os.environ.pop("RECO_INTERNAL_API_KEY", None)
            else:
                os.environ["RECO_INTERNAL_API_KEY"] = previous
        if previous_db is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_db
        reset_health_metrics()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with health_client() as test_client:
        yield test_client


def test_health_ok(client: TestClient) -> None:
    response = client.get(_HEALTH_PATH, headers=_health_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["service"] == "reco"
    assert payload["data"]["version"] == "0.1.0"
    assert "checkedAt" in payload["data"]
    assert payload["meta"]["traceId"] == _DEFAULT_TRACE_ID
    assert payload["meta"]["requestId"] == _DEFAULT_REQUEST_ID
    assert get_health_metric_count("ok") == 1


def test_health_missing_api_key(client: TestClient) -> None:
    response = client.get(_HEALTH_PATH, headers=_health_headers(include_api_key=False))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "GRS-AUTH-004"
    assert get_health_metric_count("auth_error") == 1


def test_health_invalid_api_key(client: TestClient) -> None:
    response = client.get(_HEALTH_PATH, headers=_health_headers(api_key="wrong-key"))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "GRS-AUTH-001"
    assert get_health_metric_count("auth_error") == 1


def test_health_db_unavailable(client: TestClient) -> None:
    with patch(
        "reco.api.routes.health._probe_database",
        return_value=False,
    ):
        response = client.get(_HEALTH_PATH, headers=_health_headers())
    assert response.status_code == 503
    payload = response.json()
    assert "data" not in payload
    assert payload["error"]["code"] == "GRS-COM-003"
    assert payload["meta"]["traceId"] == _DEFAULT_TRACE_ID
    assert get_health_metric_count("unavailable") == 1


def test_health_trace_optional_server_generated(client: TestClient) -> None:
    response = client.get(_HEALTH_PATH, headers=_health_headers(include_trace=False))
    assert response.status_code == 200
    meta = response.json()["meta"]
    assert meta["traceId"]
    assert meta["requestId"]
    assert meta["traceId"] != _DEFAULT_TRACE_ID
