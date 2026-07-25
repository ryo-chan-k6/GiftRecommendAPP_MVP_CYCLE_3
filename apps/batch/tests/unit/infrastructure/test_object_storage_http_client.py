"""Unit tests for S3CompatibleObjectStorageClient / create_object_storage_client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from batch.infrastructure.object_storage import (
    ObjectRef,
    ObjectStorageError,
    S3CompatibleObjectStorageClient,
    ScaffoldObjectStorageClient,
    create_object_storage_client,
    mask_object_storage_secret,
    missing_live_object_storage_credentials,
    resolve_live_object_storage_flag,
)


ACCESS_KEY = "AKIA_TEST_ACCESS_KEY"
SECRET_KEY = "secret-key-value-test"
ENDPOINT = "https://storage.example.com"


def test_create_object_storage_client_defaults_to_scaffold() -> None:
    client = create_object_storage_client(
        ACCESS_KEY, SECRET_KEY, endpoint=ENDPOINT, live=False
    )
    assert isinstance(client, ScaffoldObjectStorageClient)


def test_create_object_storage_client_live_returns_http() -> None:
    client = create_object_storage_client(
        ACCESS_KEY, SECRET_KEY, endpoint=ENDPOINT, live=True
    )
    assert isinstance(client, S3CompatibleObjectStorageClient)
    assert client.backend == "http"


def test_create_object_storage_client_live_without_endpoint_falls_back() -> None:
    client = create_object_storage_client(
        ACCESS_KEY, SECRET_KEY, endpoint=None, live=True
    )
    assert isinstance(client, ScaffoldObjectStorageClient)


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
def test_resolve_live_object_storage_flag(
    cli_live: bool, env_value: str | None, expected: bool
) -> None:
    assert (
        resolve_live_object_storage_flag(cli_live=cli_live, env_value=env_value)
        is expected
    )


def test_mask_object_storage_secret_redacts() -> None:
    masked = mask_object_storage_secret(SECRET_KEY)
    assert SECRET_KEY not in masked
    assert "REDACTED" in masked


def test_missing_live_object_storage_credentials() -> None:
    assert (
        missing_live_object_storage_credentials(
            access_key=ACCESS_KEY,
            secret_key=SECRET_KEY,
            endpoint=ENDPOINT,
        )
        is None
    )
    msg = missing_live_object_storage_credentials(
        access_key=None, secret_key=SECRET_KEY, endpoint=ENDPOINT
    )
    assert msg is not None
    assert "OBJECT_STORAGE_ACCESS_KEY" in msg


def test_put_object_success() -> None:
    response = MagicMock()
    response.status_code = 200
    response.headers = {}
    response.content = b""

    mock_client = MagicMock()
    mock_client.request.return_value = response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    client = S3CompatibleObjectStorageClient(
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        endpoint=ENDPOINT,
    )
    with patch("httpx.Client", return_value=mock_client):
        stored = client.put_object(
            ObjectRef(bucket="raw", key="raw/rakuten/x.json"),
            body=b'{"ok":true}',
            content_type="application/json",
        )

    assert stored.body == b'{"ok":true}'
    mock_client.request.assert_called_once()
    method, url = mock_client.request.call_args.args[:2]
    assert method == "PUT"
    assert url.startswith("https://storage.example.com/raw/raw/rakuten/")
    headers = mock_client.request.call_args.kwargs["headers"]
    assert "authorization" in headers
    assert ACCESS_KEY in headers["authorization"]
    assert SECRET_KEY not in str(headers)


def test_get_object_not_found_returns_none() -> None:
    response = MagicMock()
    response.status_code = 404
    response.headers = {}
    response.content = b""

    mock_client = MagicMock()
    mock_client.request.return_value = response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    client = S3CompatibleObjectStorageClient(
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        endpoint=ENDPOINT,
    )
    with patch("httpx.Client", return_value=mock_client):
        result = client.get_object(ObjectRef(bucket="raw", key="missing.json"))
    assert result is None


def test_get_object_success() -> None:
    response = MagicMock()
    response.status_code = 200
    response.headers = {"content-type": "application/json; charset=utf-8"}
    response.content = b'{"item":1}'

    mock_client = MagicMock()
    mock_client.request.return_value = response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    client = S3CompatibleObjectStorageClient(
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        endpoint=ENDPOINT,
    )
    with patch("httpx.Client", return_value=mock_client):
        stored = client.get_object(ObjectRef(bucket="raw", key="a.json"))
    assert stored is not None
    assert stored.body == b'{"item":1}'
    assert stored.content_type == "application/json"


def test_put_timeout_maps_to_error() -> None:
    mock_client = MagicMock()
    mock_client.request.side_effect = httpx.TimeoutException("timeout")
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    client = S3CompatibleObjectStorageClient(
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        endpoint=ENDPOINT,
    )
    with patch("httpx.Client", return_value=mock_client):
        with pytest.raises(ObjectStorageError) as exc_info:
            client.put_object(
                ObjectRef(bucket="raw", key="a.json"),
                body=b"x",
                content_type="application/json",
            )
    assert exc_info.value.code == "GRS-RAW-001"
    assert SECRET_KEY not in str(exc_info.value)
