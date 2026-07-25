"""Unit tests for HttpRakutenApiClient / create_rakuten_client (httpx mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from batch.infrastructure.rakuten import (
    HttpRakutenApiClient,
    ScaffoldRakutenApiClient,
    create_rakuten_client,
    mask_rakuten_secret,
    resolve_live_rakuten_flag,
)
from batch.infrastructure.rakuten.client import (
    RakutenGenreApiError,
    RakutenItemSearchApiError,
    RakutenRankingApiError,
)


APP_ID = "app-id-secret-value"
ACCESS_KEY = "access-key-secret-value"


def test_create_rakuten_client_defaults_to_scaffold() -> None:
    client = create_rakuten_client(APP_ID, ACCESS_KEY, live=False)
    assert isinstance(client, ScaffoldRakutenApiClient)


def test_create_rakuten_client_live_returns_http() -> None:
    client = create_rakuten_client(APP_ID, ACCESS_KEY, live=True)
    assert isinstance(client, HttpRakutenApiClient)
    assert client.backend == "http"


def test_create_rakuten_client_live_without_credentials_falls_back() -> None:
    client = create_rakuten_client(None, None, live=True)
    assert isinstance(client, ScaffoldRakutenApiClient)


@pytest.mark.parametrize(
    ("cli_live", "env_value", "expected"),
    [
        (False, None, False),
        (False, "0", False),
        (False, "1", True),
        (False, "true", True),
        (True, None, True),
        (True, "0", True),
    ],
)
def test_resolve_live_rakuten_flag(
    cli_live: bool, env_value: str | None, expected: bool
) -> None:
    assert resolve_live_rakuten_flag(cli_live=cli_live, env_value=env_value) is expected


def test_mask_rakuten_secret_redacts() -> None:
    masked = mask_rakuten_secret(APP_ID)
    assert APP_ID not in masked
    assert "REDACTED" in masked


def test_fetch_genre_raw_success() -> None:
    payload = {"genre": {"genreId": "100", "genreName": "Gifts"}}
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = payload

    mock_client = MagicMock()
    mock_client.get.return_value = response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    client = HttpRakutenApiClient(application_id=APP_ID, access_key=ACCESS_KEY)
    with patch("httpx.Client", return_value=mock_client):
        result = client.fetch_genre_raw(genre_id="100")

    assert result == payload
    mock_client.get.assert_called_once()
    url = mock_client.get.call_args.args[0]
    assert "openapi.rakuten.co.jp/ichibagt/api/IchibaGenre/Search/20260701" in url
    params = mock_client.get.call_args.kwargs["params"]
    assert params["applicationId"] == APP_ID
    assert params["accessKey"] == ACCESS_KEY
    assert params["genreId"] == "100"


def test_fetch_ranking_raw_omits_domain_daily_period() -> None:
    """ドメイン period=daily は楽天クエリへ送らない（現行 Ranking API）。"""

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"Items": []}

    mock_client = MagicMock()
    mock_client.get.return_value = response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    client = HttpRakutenApiClient(application_id=APP_ID, access_key=ACCESS_KEY)
    with patch("httpx.Client", return_value=mock_client):
        client.fetch_ranking_raw(genre_id="100", period="daily", page=1)

    url = mock_client.get.call_args.args[0]
    assert "openapi.rakuten.co.jp/ichibaranking/api/IchibaItem/Ranking/20220601" in url
    params = mock_client.get.call_args.kwargs["params"]
    assert "period" not in params
    assert params["genreId"] == "100"


def test_fetch_ranking_raw_sends_realtime_period() -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"Items": []}

    mock_client = MagicMock()
    mock_client.get.return_value = response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    client = HttpRakutenApiClient(application_id=APP_ID, access_key=ACCESS_KEY)
    with patch("httpx.Client", return_value=mock_client):
        client.fetch_ranking_raw(genre_id="100", period="realtime", page=1)

    params = mock_client.get.call_args.kwargs["params"]
    assert params["period"] == "realtime"


def test_fetch_ranking_raw_maps_429() -> None:
    response = MagicMock()
    response.status_code = 429

    mock_client = MagicMock()
    mock_client.get.return_value = response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    client = HttpRakutenApiClient(application_id=APP_ID, access_key=ACCESS_KEY)
    with patch("httpx.Client", return_value=mock_client):
        with pytest.raises(RakutenRankingApiError) as exc_info:
            client.fetch_ranking_raw(genre_id="100", page=1)

    assert exc_info.value.code == "GRS-EXT-102"
    assert APP_ID not in str(exc_info.value)
    assert ACCESS_KEY not in str(exc_info.value)


def test_fetch_item_search_raw_maps_timeout() -> None:
    mock_client = MagicMock()
    mock_client.get.side_effect = httpx.TimeoutException(
        f"timed out with {ACCESS_KEY}"
    )
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    client = HttpRakutenApiClient(application_id=APP_ID, access_key=ACCESS_KEY)
    with patch("httpx.Client", return_value=mock_client):
        with pytest.raises(RakutenItemSearchApiError) as exc_info:
            client.fetch_item_search_raw(cursor_type="keyword", keyword="gift", page=1)

    assert exc_info.value.code == "GRS-EXT-101"
    assert ACCESS_KEY not in str(exc_info.value)
    assert "REDACTED" in str(exc_info.value)


def test_fetch_genre_raw_maps_400() -> None:
    response = MagicMock()
    response.status_code = 400
    response.json.return_value = {
        "error": "wrong_parameter",
        "error_description": "specify valid applicationId",
    }

    mock_client = MagicMock()
    mock_client.get.return_value = response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    client = HttpRakutenApiClient(application_id=APP_ID, access_key=ACCESS_KEY)
    with patch("httpx.Client", return_value=mock_client):
        with pytest.raises(RakutenGenreApiError) as exc_info:
            client.fetch_genre_raw(genre_id="bad")

    assert exc_info.value.code == "GRS-EXT-105"
    assert "wrong_parameter" in str(exc_info.value)
    assert "specify valid applicationId" in str(exc_info.value)
    assert APP_ID not in str(exc_info.value)
