"""External AI client scaffold.

IF-EXT-005 Embedding API は MVP 初版 scaffold-first（実 OpenAI 呼出なし）。
ベクトル全文・secret をログしない。
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from typing import Protocol


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
    """IF-EXT-005 scaffold client（実 OpenAI 非呼出・1536 次元スタブ）。"""

    default_model: str = "text-embedding-3-small"
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
