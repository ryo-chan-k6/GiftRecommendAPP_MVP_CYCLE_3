"""Unit tests for MOD-BATCH-008 ExternalApiRateLimiter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from batch.infrastructure.rakuten import HttpRakutenApiClient, create_rakuten_client
from batch.infrastructure.rakuten.client import RakutenGenreApiError
from batch.infrastructure.rate_limiter import (
    DEFAULT_MAX_QPS,
    HARD_CAP_QPS,
    ExternalApiRateLimiter,
    RateLimiterConfigError,
    create_external_api_rate_limiter,
    resolve_min_interval_seconds,
)


def test_resolve_default_qps_is_two() -> None:
    interval_s, qps = resolve_min_interval_seconds()
    assert qps == DEFAULT_MAX_QPS
    assert interval_s == pytest.approx(0.5)


def test_resolve_rejects_over_hard_cap() -> None:
    with pytest.raises(RateLimiterConfigError, match="hard-cap"):
        resolve_min_interval_seconds(max_qps=HARD_CAP_QPS + 1)


def test_resolve_allows_hard_cap_qps() -> None:
    interval_s, qps = resolve_min_interval_seconds(max_qps=HARD_CAP_QPS)
    assert qps == HARD_CAP_QPS
    assert interval_s == pytest.approx(0.1)


def test_resolve_min_interval_ms_floor() -> None:
    with pytest.raises(RateLimiterConfigError, match="hard-cap"):
        resolve_min_interval_seconds(min_interval_ms=50)  # would be 20 QPS


def test_resolve_from_rakuten_max_qps_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAKUTEN_MIN_INTERVAL_MS", raising=False)
    monkeypatch.delenv("BATCH_EXTERNAL_API_MAX_QPS", raising=False)
    monkeypatch.setenv("RAKUTEN_MAX_QPS", "4")
    interval_s, qps = resolve_min_interval_seconds()
    assert qps == 4.0
    assert interval_s == pytest.approx(0.25)


def test_resolve_from_min_interval_ms_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAKUTEN_MIN_INTERVAL_MS", "250")
    interval_s, qps = resolve_min_interval_seconds()
    assert interval_s == pytest.approx(0.25)
    assert qps == pytest.approx(4.0)


def test_resolve_rejects_invalid_max_qps_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAKUTEN_MIN_INTERVAL_MS", raising=False)
    monkeypatch.setenv("RAKUTEN_MAX_QPS", "not-a-number")
    with pytest.raises(RateLimiterConfigError, match="must be a number"):
        resolve_min_interval_seconds()


def test_acquire_enforces_min_interval() -> None:
    sleeps: list[float] = []
    limiter = ExternalApiRateLimiter(min_interval_seconds=0.5, effective_qps=2.0)

    limiter.acquire(sleep=sleeps.append)
    limiter.acquire(sleep=sleeps.append)

    assert limiter.acquire_count == 2
    assert len(sleeps) == 1
    assert sleeps[0] == pytest.approx(0.5, abs=0.05)


def test_wait_after_rate_limit_uses_backoff() -> None:
    sleeps: list[float] = []
    limiter = ExternalApiRateLimiter(
        min_interval_seconds=0.5,
        effective_qps=2.0,
        backoff_seconds_on_429=1.5,
    )
    waited = limiter.wait_after_rate_limit(sleep=sleeps.append)
    assert waited == 1.5
    assert sleeps == [1.5]
    assert limiter.rate_limit_wait_count == 1


def test_create_external_api_rate_limiter_can_disable() -> None:
    assert create_external_api_rate_limiter(enabled=False) is None


def test_create_rakuten_client_attaches_limiter() -> None:
    client = create_rakuten_client("app-id", "access-key", live=True)
    assert isinstance(client, HttpRakutenApiClient)
    assert isinstance(client.rate_limiter, ExternalApiRateLimiter)
    assert client.rate_limiter.effective_qps == DEFAULT_MAX_QPS


def test_create_rakuten_client_can_skip_limiter() -> None:
    client = create_rakuten_client(
        "app-id",
        "access-key",
        live=True,
        enable_rate_limiter=False,
    )
    assert isinstance(client, HttpRakutenApiClient)
    assert client.rate_limiter is None


def test_http_client_acquires_before_http_get() -> None:
    """送信前 acquire が HTTP GET より先であることを順序検証する。"""
    call_order: list[str] = []

    class OrderLimiter(ExternalApiRateLimiter):
        def acquire(self, *, sleep=None) -> float:  # type: ignore[no-untyped-def]
            call_order.append("acquire")
            return super().acquire(sleep=sleep)

    limiter = OrderLimiter(
        min_interval_seconds=0.0,
        effective_qps=2.0,
        max_retries_on_429=0,
        backoff_seconds_on_429=0.0,
    )
    client = HttpRakutenApiClient(
        application_id="app-id",
        access_key="access-key",
        rate_limiter=limiter,
    )

    ok = MagicMock()
    ok.status_code = 200
    ok.json.return_value = {"genre": {"genreId": "0"}}
    mock_http = MagicMock()

    def _get(*_args: object, **_kwargs: object) -> MagicMock:
        call_order.append("get")
        return ok

    mock_http.get.side_effect = _get
    mock_http.__enter__.return_value = mock_http
    mock_http.__exit__.return_value = None

    with patch("httpx.Client", return_value=mock_http):
        client.fetch_genre_raw(genre_id="0")

    assert call_order == ["acquire", "get"]
    assert limiter.acquire_count == 1


def test_http_client_retries_429_then_succeeds() -> None:
    limiter = ExternalApiRateLimiter(
        min_interval_seconds=0.0,
        effective_qps=2.0,
        max_retries_on_429=2,
        backoff_seconds_on_429=0.0,
    )
    client = HttpRakutenApiClient(
        application_id="app-id",
        access_key="access-key",
        rate_limiter=limiter,
    )

    rate_limited = MagicMock()
    rate_limited.status_code = 429
    ok = MagicMock()
    ok.status_code = 200
    ok.json.return_value = {"genre": {"genreId": "0"}}

    mock_http = MagicMock()
    mock_http.get.side_effect = [rate_limited, ok]
    mock_http.__enter__.return_value = mock_http
    mock_http.__exit__.return_value = None

    with patch("httpx.Client", return_value=mock_http):
        payload = client.fetch_genre_raw(genre_id="0")

    assert payload["genre"]["genreId"] == "0"
    assert mock_http.get.call_count == 2
    assert limiter.rate_limit_wait_count == 1


def test_http_client_raises_102_after_retries_exhausted() -> None:
    limiter = ExternalApiRateLimiter(
        min_interval_seconds=0.0,
        effective_qps=2.0,
        max_retries_on_429=1,
        backoff_seconds_on_429=0.0,
    )
    client = HttpRakutenApiClient(
        application_id="app-id",
        access_key="access-key",
        rate_limiter=limiter,
    )

    rate_limited = MagicMock()
    rate_limited.status_code = 429
    mock_http = MagicMock()
    mock_http.get.return_value = rate_limited
    mock_http.__enter__.return_value = mock_http
    mock_http.__exit__.return_value = None

    with patch("httpx.Client", return_value=mock_http):
        with pytest.raises(RakutenGenreApiError) as exc_info:
            client.fetch_genre_raw(genre_id="0")

    assert exc_info.value.code == "GRS-EXT-102"
    assert mock_http.get.call_count == 2  # initial + 1 retry
