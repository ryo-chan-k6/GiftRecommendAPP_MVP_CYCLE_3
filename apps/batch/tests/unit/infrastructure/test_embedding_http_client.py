"""Unit tests for HttpEmbeddingClient / create_embedding_client (httpx mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from batch.infrastructure.external_ai import (
    EmbeddingApiError,
    HttpEmbeddingClient,
    ScaffoldEmbeddingClient,
    create_embedding_client,
    mask_openai_secret,
    resolve_live_embedding_flag,
)


API_KEY = "sk-test-openai-secret-value"


def test_create_embedding_client_defaults_to_scaffold() -> None:
    client = create_embedding_client(API_KEY, live=False)
    assert isinstance(client, ScaffoldEmbeddingClient)


def test_create_embedding_client_live_returns_http() -> None:
    client = create_embedding_client(API_KEY, live=True)
    assert isinstance(client, HttpEmbeddingClient)
    assert client.backend == "http"


def test_create_embedding_client_live_without_key_falls_back() -> None:
    client = create_embedding_client(None, live=True)
    assert isinstance(client, ScaffoldEmbeddingClient)


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
def test_resolve_live_embedding_flag(
    cli_live: bool, env_value: str | None, expected: bool
) -> None:
    assert resolve_live_embedding_flag(cli_live=cli_live, env_value=env_value) is expected


def test_mask_openai_secret_redacts() -> None:
    masked = mask_openai_secret(API_KEY)
    assert API_KEY not in masked
    assert "REDACTED" in masked


def test_embed_success() -> None:
    vector = [0.1, 0.2, 0.3]
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "model": "text-embedding-3-small",
        "data": [{"embedding": vector}],
    }

    mock_client = MagicMock()
    mock_client.post.return_value = response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    client = HttpEmbeddingClient(api_key=API_KEY)
    with patch("httpx.Client", return_value=mock_client):
        result = client.embed(
            "hello",
            model="text-embedding-3-small",
            dimension=3,
            purpose="item_embedding",
        )

    assert result.dimension == 3
    assert result.embedding_vector == (0.1, 0.2, 0.3)
    assert result.model == "text-embedding-3-small"
    mock_client.post.assert_called_once()
    url = mock_client.post.call_args.args[0]
    assert url == "https://api.openai.com/v1/embeddings"
    headers = mock_client.post.call_args.kwargs["headers"]
    assert headers["Authorization"] == f"Bearer {API_KEY}"
    payload = mock_client.post.call_args.kwargs["json"]
    assert payload["model"] == "text-embedding-3-small"
    assert payload["input"] == "hello"
    assert payload["dimensions"] == 3


def test_embed_timeout_maps_to_grs_ext_101() -> None:
    mock_client = MagicMock()
    mock_client.post.side_effect = httpx.TimeoutException("timeout")
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    client = HttpEmbeddingClient(api_key=API_KEY)
    with patch("httpx.Client", return_value=mock_client):
        with pytest.raises(EmbeddingApiError) as exc_info:
            client.embed("x", model="m", dimension=3, purpose="t")
    assert exc_info.value.code == "GRS-EXT-101"
    assert API_KEY not in str(exc_info.value)


def test_embed_http_429_maps_to_grs_ext_102() -> None:
    response = MagicMock()
    response.status_code = 429
    mock_client = MagicMock()
    mock_client.post.return_value = response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    client = HttpEmbeddingClient(api_key=API_KEY)
    with patch("httpx.Client", return_value=mock_client):
        with pytest.raises(EmbeddingApiError) as exc_info:
            client.embed("x", model="m", dimension=3, purpose="t")
    assert exc_info.value.code == "GRS-EXT-102"


def test_embed_dimension_mismatch_maps_to_grs_llm_103() -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "model": "text-embedding-3-small",
        "data": [{"embedding": [0.1, 0.2]}],
    }
    mock_client = MagicMock()
    mock_client.post.return_value = response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    client = HttpEmbeddingClient(api_key=API_KEY)
    with patch("httpx.Client", return_value=mock_client):
        with pytest.raises(EmbeddingApiError) as exc_info:
            client.embed("x", model="m", dimension=3, purpose="t")
    assert exc_info.value.code == "GRS-LLM-103"


def test_embed_invalid_json_maps_to_grs_ext_103() -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.side_effect = ValueError("bad json")
    mock_client = MagicMock()
    mock_client.post.return_value = response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    client = HttpEmbeddingClient(api_key=API_KEY)
    with patch("httpx.Client", return_value=mock_client):
        with pytest.raises(EmbeddingApiError) as exc_info:
            client.embed("x", model="m", dimension=3, purpose="t")
    assert exc_info.value.code == "GRS-EXT-103"
