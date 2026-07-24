"""Object storage clients (IF-STG-001 / IF-STG-002).

``ScaffoldObjectStorageClient``（既定）と ``S3CompatibleObjectStorageClient``（明示 live）。
secret をログしない。
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import quote, urlparse


@dataclass(frozen=True)
class ObjectRef:
    """Reference to a stored object."""

    bucket: str
    key: str


@dataclass(frozen=True)
class StoredObject:
    """Object payload placeholder."""

    ref: ObjectRef
    content_type: str
    body: bytes


class ObjectStorageError(Exception):
    """Raised when Object Storage put/get fails (mapped to GRS-RAW-* in job layer)."""

    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class ObjectStorageClient(Protocol):
    """Object storage boundary for Raw JSON persistence (Phase4a protocol)."""

    def put_object(
        self,
        ref: ObjectRef,
        *,
        body: bytes,
        content_type: str,
    ) -> StoredObject: ...

    def get_object(self, ref: ObjectRef) -> StoredObject | None: ...


def mask_object_storage_secret(value: str) -> str:
    """Redact Object Storage secrets that may appear in error strings."""

    if value.strip() == "":
        return ""
    if len(value) <= 8:
        return "***REDACTED***"
    return f"{value[:2]}***REDACTED***{value[-2:]}"


def _mask_text(text: str, *, secrets: tuple[str, ...]) -> str:
    masked = text
    for secret in secrets:
        if secret and secret in masked:
            masked = masked.replace(secret, mask_object_storage_secret(secret))
    return masked


def _uri_encode(value: str, *, encode_slash: bool = True) -> str:
    safe = "" if encode_slash else "/"
    return quote(value, safe=safe)


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(*, secret_key: str, date_stamp: str, region: str, service: str) -> bytes:
    k_date = _sign(("AWS4" + secret_key).encode("utf-8"), date_stamp)
    k_region = hmac.new(k_date, region.encode("utf-8"), hashlib.sha256).digest()
    k_service = hmac.new(k_region, service.encode("utf-8"), hashlib.sha256).digest()
    return hmac.new(k_service, b"aws4_request", hashlib.sha256).digest()


@dataclass
class ScaffoldObjectStorageClient:
    """Phase4a in-memory object store for unit tests."""

    objects: dict[tuple[str, str], StoredObject] = field(default_factory=dict)
    put_calls: list[dict[str, object]] = field(default_factory=list)
    get_calls: list[ObjectRef] = field(default_factory=list)
    fail_on_put: bool = False
    # N 回 put 成功後に失敗させる（同一 Run 内の部分失敗を unit で再現するため）
    fail_after_n_puts: int | None = None
    backend: str = "scaffold"

    def put_object(
        self,
        ref: ObjectRef,
        *,
        body: bytes,
        content_type: str,
    ) -> StoredObject:
        if self.fail_on_put:
            raise ObjectStorageError(code="GRS-RAW-001", message="scaffold forced put failure")
        if (
            self.fail_after_n_puts is not None
            and len(self.put_calls) >= self.fail_after_n_puts
        ):
            raise ObjectStorageError(
                code="GRS-RAW-001",
                message="scaffold forced put failure after successful puts",
            )
        stored = StoredObject(ref=ref, content_type=content_type, body=body)
        self.objects[(ref.bucket, ref.key)] = stored
        self.put_calls.append(
            {
                "ref": ref,
                "body": body,
                "content_type": content_type,
            }
        )
        return stored

    def get_object(self, ref: ObjectRef) -> StoredObject | None:
        self.get_calls.append(ref)
        return self.objects.get((ref.bucket, ref.key))


@dataclass
class S3CompatibleObjectStorageClient:
    """IF-STG S3-compatible Object Storage client (path-style + SigV4).

    Secrets are never logged. Uses existing ``httpx`` dependency (no boto3).
    """

    access_key: str
    secret_key: str
    endpoint: str
    region: str = "us-east-1"
    timeout_seconds: float = 30.0
    backend: str = "http"
    service: str = "s3"

    def put_object(
        self,
        ref: ObjectRef,
        *,
        body: bytes,
        content_type: str,
    ) -> StoredObject:
        status, _response_headers, _response_body = self._request(
            method="PUT",
            ref=ref,
            body=body,
            content_type=content_type or "application/octet-stream",
        )
        if status in {200, 201}:
            return StoredObject(ref=ref, content_type=content_type, body=body)
        if status == 404:
            raise ObjectStorageError(
                code="GRS-RAW-001",
                message=f"object storage put not found (HTTP {status})",
            )
        raise ObjectStorageError(
            code="GRS-RAW-001",
            message=f"object storage put failed (HTTP {status})",
        )

    def get_object(self, ref: ObjectRef) -> StoredObject | None:
        status, response_headers, response_body = self._request(
            method="GET",
            ref=ref,
            body=b"",
            content_type="",
        )
        if status == 404:
            return None
        if status != 200:
            raise ObjectStorageError(
                code="GRS-RAW-004",
                message=f"object storage get failed (HTTP {status})",
            )
        content_type = response_headers.get("content-type") or "application/octet-stream"
        # strip charset etc.
        content_type = content_type.split(";", 1)[0].strip() or "application/octet-stream"
        return StoredObject(ref=ref, content_type=content_type, body=response_body)

    def _request(
        self,
        *,
        method: str,
        ref: ObjectRef,
        body: bytes,
        content_type: str,
    ) -> tuple[int, dict[str, str], bytes]:
        import httpx

        secrets = (self.access_key, self.secret_key)
        url, host, canonical_uri = self._build_url(ref)
        amz_date, date_stamp = self._amz_timestamps()
        payload_hash = _sha256_hex(body)

        headers: dict[str, str] = {
            "host": host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        }
        if content_type:
            headers["content-type"] = content_type

        _signed_headers, authorization = self._authorization(
            method=method,
            canonical_uri=canonical_uri,
            headers=headers,
            payload_hash=payload_hash,
            amz_date=amz_date,
            date_stamp=date_stamp,
        )
        headers["authorization"] = authorization

        request_headers = {key: value for key, value in headers.items() if key != "host"}
        # httpx sets Host from URL; keep signed host consistent via URL.
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.request(
                    method,
                    url,
                    content=body if method != "GET" else None,
                    headers=request_headers,
                )
        except httpx.TimeoutException as exc:
            message = _mask_text(str(exc), secrets=secrets)
            raise ObjectStorageError(
                code="GRS-RAW-001" if method == "PUT" else "GRS-RAW-004",
                message=f"object storage timeout: {message}",
            ) from exc
        except httpx.HTTPError as exc:
            message = _mask_text(str(exc), secrets=secrets)
            raise ObjectStorageError(
                code="GRS-RAW-001" if method == "PUT" else "GRS-RAW-004",
                message=f"object storage transport error: {message}",
            ) from exc

        response_headers = {k.lower(): v for k, v in response.headers.items()}
        return response.status_code, response_headers, response.content

    def _build_url(self, ref: ObjectRef) -> tuple[str, str, str]:
        endpoint = self.endpoint.rstrip("/")
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ObjectStorageError(
                code="GRS-RAW-001",
                message="object storage endpoint must be an absolute http(s) URL",
            )
        # path-style: {endpoint}/{bucket}/{key}
        key_path = "/".join(_uri_encode(part, encode_slash=True) for part in ref.key.split("/"))
        bucket_enc = _uri_encode(ref.bucket, encode_slash=True)
        base_path = parsed.path.rstrip("/")
        canonical_uri = f"{base_path}/{bucket_enc}/{key_path}"
        if not canonical_uri.startswith("/"):
            canonical_uri = "/" + canonical_uri
        url = f"{parsed.scheme}://{parsed.netloc}{canonical_uri}"
        return url, parsed.netloc, canonical_uri

    def _amz_timestamps(self) -> tuple[str, str]:
        now = datetime.now(UTC)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        return amz_date, date_stamp

    def _authorization(
        self,
        *,
        method: str,
        canonical_uri: str,
        headers: dict[str, str],
        payload_hash: str,
        amz_date: str,
        date_stamp: str,
    ) -> tuple[str, str]:
        signed_header_keys = sorted(headers.keys())
        signed_headers = ";".join(signed_header_keys)
        canonical_headers = "".join(f"{key}:{headers[key].strip()}\n" for key in signed_header_keys)
        canonical_request = "\n".join(
            [
                method,
                canonical_uri,
                "",  # no query string for put/get by key
                canonical_headers,
                signed_headers,
                payload_hash,
            ]
        )
        credential_scope = f"{date_stamp}/{self.region}/{self.service}/aws4_request"
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                _sha256_hex(canonical_request.encode("utf-8")),
            ]
        )
        signature = hmac.new(
            _signing_key(
                secret_key=self.secret_key,
                date_stamp=date_stamp,
                region=self.region,
                service=self.service,
            ),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        authorization = (
            "AWS4-HMAC-SHA256 "
            f"Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )
        return signed_headers, authorization


def create_object_storage_client(
    access_key: str | None,
    secret_key: str | None,
    *,
    endpoint: str | None,
    region: str = "us-east-1",
    live: bool = False,
    fallback: ObjectStorageClient | None = None,
) -> ObjectStorageClient:
    """Build an ObjectStorageClient.

    - ``live=False``（既定）→ Scaffold
    - ``live=True`` かつ access/secret/endpoint あり → S3CompatibleObjectStorageClient
    - ``live=True`` だが不足 → Scaffold（呼び出し側で exit 2 を推奨）
    """

    if live and access_key and secret_key and endpoint:
        return S3CompatibleObjectStorageClient(
            access_key=access_key,
            secret_key=secret_key,
            endpoint=endpoint,
            region=region,
        )
    return fallback or ScaffoldObjectStorageClient()


def resolve_live_object_storage_flag(*, cli_live: bool, env_value: str | None) -> bool:
    """Resolve live flag from CLI and ``BATCH_OBJECT_STORAGE_LIVE`` env."""

    if cli_live:
        return True
    if env_value is None:
        return False
    return env_value.strip().lower() in {"1", "true", "yes", "on"}


def missing_live_object_storage_credentials(
    *,
    access_key: str | None,
    secret_key: str | None,
    endpoint: str | None,
) -> str | None:
    """Return a human-readable error if live Object Storage credentials are incomplete."""

    missing: list[str] = []
    if not access_key:
        missing.append("OBJECT_STORAGE_ACCESS_KEY")
    if not secret_key:
        missing.append("OBJECT_STORAGE_SECRET_KEY")
    if not endpoint:
        missing.append("OBJECT_STORAGE_ENDPOINT")
    if not missing:
        return None
    return (
        f"{', '.join(missing)} are required for --live-object-storage. "
        "Use --scaffold-demo for local/CI."
    )
