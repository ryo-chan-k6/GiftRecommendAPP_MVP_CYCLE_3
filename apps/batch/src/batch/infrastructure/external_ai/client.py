"""External AI / Embedding clients.

IF-EXT-005: ``ScaffoldEmbeddingClient``（既定）と ``HttpEmbeddingClient``（明示 live）。
ベクトル全文・secret をログしない。
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from typing import Protocol


_OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
_DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


@dataclass(frozen=True)
class ExternalAiResponse:
    """External AI completion placeholder."""

    text: str
    model: str


@dataclass(frozen=True)
class EmbeddingResponse:
    """IF-EXT-005 Embedding API 応答（scaffold / 実 API 共通契約）。"""

    embedding_vector: tuple[float, ...]
    model: str
    dimension: int


class ExternalAiClient(Protocol):
    """External AI API boundary for embeddings and LLM calls (Phase4a protocol)."""

    def generate(self, prompt: str, *, purpose: str) -> ExternalAiResponse: ...


class EmbeddingClient(Protocol):
    """IF-EXT-005 Embedding API boundary."""

    def embed(
        self,
        text: str,
        *,
        model: str,
        dimension: int,
        purpose: str,
    ) -> EmbeddingResponse: ...


class EmbeddingApiError(Exception):
    """Raised when Embedding HTTP fails (mapped to GRS-EXT-* / GRS-LLM-*)."""

    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _deterministic_stub_vector(*, seed_text: str, dimension: int) -> tuple[float, ...]:
    """hash 由来の決定論的疑似ベクトル（次元契約検証用）。"""

    values: list[float] = []
    counter = 0
    while len(values) < dimension:
        digest = hashlib.sha256(f"{seed_text}:{counter}".encode("utf-8")).digest()
        for i in range(0, len(digest) - 3, 4):
            raw = struct.unpack_from(">I", digest, i)[0]
            values.append((raw / 0xFFFFFFFF) * 2.0 - 1.0)
            if len(values) >= dimension:
                break
        counter += 1
    return tuple(values[:dimension])


def mask_openai_secret(value: str) -> str:
    """Redact OpenAI API keys that may appear in error strings."""

    if value.strip() == "":
        return ""
    if len(value) <= 8:
        return "***REDACTED***"
    return f"{value[:2]}***REDACTED***{value[-2:]}"


def _mask_text(text: str, *, secrets: tuple[str, ...]) -> str:
    masked = text
    for secret in secrets:
        if secret and secret in masked:
            masked = masked.replace(secret, mask_openai_secret(secret))
    return masked


@dataclass
class ScaffoldExternalAiClient:
    """Phase4a placeholder client without outbound API calls."""

    model: str = "scaffold"
    generate_calls: list[dict[str, str]] = field(default_factory=list)

    def generate(self, prompt: str, *, purpose: str) -> ExternalAiResponse:
        self.generate_calls.append({"prompt": prompt, "purpose": purpose})
        return ExternalAiResponse(
            text=f"[scaffold:{purpose}]",
            model=self.model,
        )


@dataclass
class ScaffoldEmbeddingClient:
    """IF-EXT-005 scaffold client（実 OpenAI 非呼出・決定論的スタブ）。"""

    default_model: str = _DEFAULT_EMBEDDING_MODEL
    backend: str = "scaffold"
    embed_calls: list[dict[str, object]] = field(default_factory=list)

    def embed(
        self,
        text: str,
        *,
        model: str,
        dimension: int,
        purpose: str,
    ) -> EmbeddingResponse:
        # 入力全文・ベクトル全文は記録しない（メタのみ）
        self.embed_calls.append(
            {
                "purpose": purpose,
                "model": model,
                "dimension": dimension,
                "input_chars": len(text),
            }
        )
        vector = _deterministic_stub_vector(seed_text=text, dimension=dimension)
        return EmbeddingResponse(
            embedding_vector=vector,
            model=model or self.default_model,
            dimension=len(vector),
        )


@dataclass
class HttpEmbeddingClient:
    """IF-EXT-005 OpenAI Embeddings HTTP client.

    Secrets / vector bodies are never logged.
    """

    api_key: str
    timeout_seconds: float = 30.0
    backend: str = "http"
    base_url: str = _OPENAI_EMBEDDINGS_URL

    def embed(
        self,
        text: str,
        *,
        model: str,
        dimension: int,
        purpose: str,
    ) -> EmbeddingResponse:
        import httpx

        _ = purpose  # call-site purpose; not sent to OpenAI
        secrets = (self.api_key,)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, object] = {
            "model": model or _DEFAULT_EMBEDDING_MODEL,
            "input": text,
        }
        if dimension > 0:
            payload["dimensions"] = dimension

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(self.base_url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            message = _mask_text(str(exc), secrets=secrets)
            raise EmbeddingApiError(
                code="GRS-EXT-101",
                message=f"openai embeddings timeout: {message}",
            ) from exc
        except httpx.HTTPError as exc:
            message = _mask_text(str(exc), secrets=secrets)
            raise EmbeddingApiError(
                code="GRS-EXT-100",
                message=f"openai embeddings transport error: {message}",
            ) from exc

        if response.status_code == 429:
            raise EmbeddingApiError(
                code="GRS-EXT-102",
                message="openai embeddings rate limited (HTTP 429)",
            )
        if response.status_code == 401:
            raise EmbeddingApiError(
                code="GRS-EXT-100",
                message="openai embeddings unauthorized (HTTP 401)",
            )
        if response.status_code >= 400:
            raise EmbeddingApiError(
                code="GRS-EXT-100",
                message=f"openai embeddings HTTP {response.status_code}",
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise EmbeddingApiError(
                code="GRS-EXT-103",
                message="openai embeddings invalid JSON response",
            ) from exc
        if not isinstance(body, dict):
            raise EmbeddingApiError(
                code="GRS-EXT-103",
                message="openai embeddings response is not an object",
            )

        data = body.get("data")
        if not isinstance(data, list) or not data:
            raise EmbeddingApiError(
                code="GRS-EXT-103",
                message="openai embeddings response missing data[]",
            )
        first = data[0]
        if not isinstance(first, dict):
            raise EmbeddingApiError(
                code="GRS-EXT-103",
                message="openai embeddings response data[0] invalid",
            )
        vector_raw = first.get("embedding")
        if not isinstance(vector_raw, list) or not vector_raw:
            raise EmbeddingApiError(
                code="GRS-LLM-103",
                message="openai embeddings response missing embedding vector",
            )

        vector = tuple(float(value) for value in vector_raw)
        model_used = body.get("model")
        resolved_model = (
            str(model_used)
            if isinstance(model_used, str) and model_used
            else (model or _DEFAULT_EMBEDDING_MODEL)
        )
        if dimension > 0 and len(vector) != dimension:
            raise EmbeddingApiError(
                code="GRS-LLM-103",
                message=(
                    f"openai embeddings dimension mismatch: "
                    f"expected={dimension} actual={len(vector)}"
                ),
            )
        return EmbeddingResponse(
            embedding_vector=vector,
            model=resolved_model,
            dimension=len(vector),
        )


def create_embedding_client(
    api_key: str | None,
    *,
    live: bool = False,
    fallback: EmbeddingClient | None = None,
) -> EmbeddingClient:
    """Build an EmbeddingClient.

    - ``live=False``（既定）→ Scaffold
    - ``live=True`` かつ api_key あり → HttpEmbeddingClient
    - ``live=True`` だが api_key 不足 → Scaffold（呼び出し側で exit 2 を推奨）
    """

    if live and api_key:
        return HttpEmbeddingClient(api_key=api_key)
    return fallback or ScaffoldEmbeddingClient()


def resolve_live_embedding_flag(*, cli_live: bool, env_value: str | None) -> bool:
    """Resolve live flag from CLI and ``BATCH_EMBEDDING_LIVE`` env."""

    if cli_live:
        return True
    if env_value is None:
        return False
    return env_value.strip().lower() in {"1", "true", "yes", "on"}
