#!/usr/bin/env python3
"""OpenAI HTTP clients for Phase2 live bench (scripts/perf only).

apps/reco の scaffold クライアントを差し替えるための PoC 用実装。
secret 実値は環境変数からのみ読み取り、ログ・例外メッセージへ出さない。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import httpx

from reco.infrastructure.external_ai.client import ExternalAiResponse

_OPENAI_BASE_URL = "https://api.openai.com/v1"
_DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
_DEFAULT_CHAT_MODEL = "gpt-4o-mini"
_TIMEOUT_S = 30.0
_EMBEDDING_DIMENSIONS = 1536


def _require_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "openai_mode=secrets には OPENAI_API_KEY が必要です。"
            " 実値は env / GitHub Secrets からのみ注入し、成果物へ記載しません。"
        )
    return api_key


def _redacted_http_error(exc: httpx.HTTPError) -> str:
    """Avoid echoing response bodies that might contain sensitive upstream data."""
    return f"{type(exc).__name__} (status/details redacted for bench safety)"


@dataclass
class HttpOpenAiEmbeddingClient:
    """IF-EXT-005 相当の Embedding API 実疎通クライアント（bench 専用）。"""

    model: str = _DEFAULT_EMBEDDING_MODEL
    timeout_s: float = _TIMEOUT_S
    generate_calls: list[dict[str, object]] = field(default_factory=list)
    _api_key: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self._api_key:
            self._api_key = _require_api_key()

    def generate(
        self,
        text: str,
        model_version_id: str,
        metadata: dict[str, str],
    ):
        from reco.application.query_embedding_generator.ports import (
            EmbeddingGenerationResult,
        )

        self.generate_calls.append(
            {
                "text_len": len(text),
                "model_version_id": model_version_id,
                "metadata_keys": sorted(metadata.keys()),
                "model": self.model,
            }
        )
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": text,
            "dimensions": _EMBEDDING_DIMENSIONS,
        }
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                response = client.post(
                    f"{_OPENAI_BASE_URL}/embeddings",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"OpenAI embeddings request failed: {_redacted_http_error(exc)}"
            ) from None

        data = body.get("data")
        if not isinstance(data, list) or not data:
            raise RuntimeError("OpenAI embeddings response missing data[]")
        first = data[0]
        if not isinstance(first, dict):
            raise RuntimeError("OpenAI embeddings response data[0] invalid")
        vector_raw = first.get("embedding")
        if not isinstance(vector_raw, list) or not vector_raw:
            raise RuntimeError("OpenAI embeddings response missing embedding vector")
        vector = tuple(float(value) for value in vector_raw)
        return EmbeddingGenerationResult(
            vector=vector,
            model_version_id=model_version_id,
            dimensions=len(vector),
        )


@dataclass
class HttpOpenAiLlmClient:
    """ExternalAiClient Protocol 互換の Chat Completions 実疎通（bench 専用）。"""

    model: str = _DEFAULT_CHAT_MODEL
    timeout_s: float = _TIMEOUT_S
    generate_calls: list[dict[str, str]] = field(default_factory=list)
    _api_key: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self._api_key:
            self._api_key = _require_api_key()

    def generate(self, prompt: str, *, purpose: str) -> ExternalAiResponse:
        self.generate_calls.append({"purpose": purpose, "prompt_len": str(len(prompt))})
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        system = (
            "You are a JSON-only assistant for gift semantic extraction. "
            'Respond with a single JSON object: {"concepts":[{"concept_code":"...","confidence":0.0,'
            '"input_intent":"neutral","evidence_texts":[]}]}'
        )
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                response = client.post(
                    f"{_OPENAI_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"OpenAI chat request failed: {_redacted_http_error(exc)}"
            ) from None

        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("OpenAI chat response missing choices[]")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            content = json.dumps({"concepts": []})
        return ExternalAiResponse(text=content, model=self.model)
