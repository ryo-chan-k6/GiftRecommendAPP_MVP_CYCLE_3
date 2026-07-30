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


def test_health_probes_shared_lifespan_session(client: TestClient) -> None:
    with patch(
        "reco.api.routes.health._probe_database",
        return_value=True,
    ) as probe:
        response = client.get(_HEALTH_PATH, headers=_health_headers())

    assert response.status_code == 200
    shared_session = probe.call_args.args[0]
    assert shared_session.backend == "scaffold"


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


def test_health_trace_propagation_exact_match(client: TestClient) -> None:
    """実装仕様書 §10 No.5: X-Trace-Id 指定時に meta.traceId が一致する。"""
    response = client.get(_HEALTH_PATH, headers=_health_headers())
    assert response.status_code == 200
    meta = response.json()["meta"]
    assert meta["traceId"] == _DEFAULT_TRACE_ID
    assert meta["requestId"] == _DEFAULT_REQUEST_ID


def test_health_idempotent_repeated_ok(client: TestClient) -> None:
    """実装仕様書 §10 No.6 / 契約 §12 No.4: 連続呼び出しで副作用なし（カウンタ以外）。"""
    first = client.get(_HEALTH_PATH, headers=_health_headers())
    second = client.get(_HEALTH_PATH, headers=_health_headers())
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["status"] == "ok"
    assert second.json()["data"]["status"] == "ok"
    assert first.json()["data"]["service"] == second.json()["data"]["service"] == "reco"
    # metric は加算されるが、Response 外形は同一（副作用なし）
    assert get_health_metric_count("ok") == 2
    assert get_health_metric_count() == 2


def test_health_response_and_metric_log_do_not_leak_secrets(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """実装仕様書 §10 No.8: Response / metric ログに Key・DATABASE_URL 実値を出さない。"""
    secret_key = _TEST_INTERNAL_API_KEY
    with caplog.at_level("INFO", logger="reco.api.health.metric"):
        response = client.get(_HEALTH_PATH, headers=_health_headers())
    assert response.status_code == 200
    body_text = response.text
    assert secret_key not in body_text
    assert "DATABASE_URL" not in body_text
    assert "postgresql://" not in body_text.lower()
    # metric 構造化ログにも Key 実値を含めない
    joined = "\n".join(record.getMessage() for record in caplog.records)
    assert secret_key not in joined
    assert "DATABASE_URL" not in joined
