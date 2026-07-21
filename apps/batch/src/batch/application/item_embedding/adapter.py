"""IF-EXT-005 Item Embedding 生成アダプタ（MVP Scaffold）.

仕様書 §8.3 / §18.1 No.8:
- MVP 初版は scaffold-first（実 OpenAI 呼出なし）
- 決定論的スタブベクトル（次元 1536）
- hash 再算出禁止（IF-DB-BATCH-015 消費のみ）
- ベクトル全文・secret をログしない

apps/reco を変更せず、batch 内に Protocol 互換の Scaffold 実装を置く。
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from batch.application.item_embedding.models import (
    EMBEDDING_DIMENSION,
    EmbeddingGenerationContext,
    EmbeddingGenerationResult,
)
from batch.infrastructure.external_ai.client import (
    EmbeddingResponse,
    ScaffoldEmbeddingClient,
)

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def is_valid_embedding_input_hash(value: str | None) -> bool:
    """SHA-256 lowercase hex (64 chars) か検証。再算出はしない。"""

    return bool(value) and bool(_HEX64.match(value or ""))


def serialize_embedding_input(item_text_context: dict[str, Any]) -> str:
    """item_text_context → Embedding API 入力文字列（BATCH-014 canonicalize と整合）。"""

    return json.dumps(
        item_text_context,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def build_deterministic_stub_vector(
    *,
    seed_text: str,
    dimension: int = EMBEDDING_DIMENSION,
) -> tuple[float, ...]:
    """hash 由来の決定論的疑似ベクトル（§18.2 No.4）。実 OpenAI 形式に合わせ float 列."""

    if dimension <= 0:
        raise ValueError("dimension must be positive")
    values: list[float] = []
    counter = 0
    while len(values) < dimension:
        digest = hashlib.sha256(f"{seed_text}:{counter}".encode("utf-8")).digest()
        for i in range(0, len(digest) - 3, 4):
            raw = struct.unpack_from(">I", digest, i)[0]
            # Map to roughly [-1, 1) without logging the vector itself.
            values.append((raw / 0xFFFFFFFF) * 2.0 - 1.0)
            if len(values) >= dimension:
                break
        counter += 1
    return tuple(values[:dimension])


class ItemEmbeddingGeneratorPort(Protocol):
    """IF-EXT-005 Port（MOD-BATCH-036 Batch-facing）。"""

    def generate_item_embedding(
        self,
        context: EmbeddingGenerationContext,
    ) -> EmbeddingGenerationResult: ...


@dataclass
class ScaffoldItemEmbeddingAdapter:
    """MVP Scaffold: IF-EXT-005 スタブ / Upsert 非実施 / 実 API 非呼出."""

    client: ScaffoldEmbeddingClient = field(default_factory=ScaffoldEmbeddingClient)
    force_fail: bool = False

    def generate_item_embedding(
        self,
        context: EmbeddingGenerationContext,
    ) -> EmbeddingGenerationResult:
        if not context.trace_id.strip():
            return self._failed("trace_id is required")
        if not context.item_id.strip() or not context.model_version_id.strip():
            return self._failed("item_id / model_version_id required")
        if not is_valid_embedding_input_hash(context.embedding_input_hash):
            return self._failed("embedding_input_hash must be 64 hex")
        if context.embedding_source_type != "item_text_context":
            return self._failed("embedding_source_type must be item_text_context")
        if not context.embedding_input_text.strip():
            return self._failed("embedding_input_text is required")
        if context.dimension != EMBEDDING_DIMENSION:
            return self._failed(f"dimension must be {EMBEDDING_DIMENSION}")
        if self.force_fail:
            return self._failed("scaffold forced failure", code="GRS-EXT-001")

        started = time.perf_counter()
        response: EmbeddingResponse = self.client.embed(
            context.embedding_input_text,
            model=context.model_name,
            dimension=context.dimension,
            purpose="item_embedding",
        )
        latency_ms = int((time.perf_counter() - started) * 1000)

        if len(response.embedding_vector) != context.dimension:
            return self._failed("scaffold embedding dimension mismatch", code="GRS-EXT-001")

        return EmbeddingGenerationResult(
            status="generated",
            embedding_vector=response.embedding_vector,
            model_name=response.model,
            dimension=len(response.embedding_vector),
            latency_ms=latency_ms,
        )

    @staticmethod
    def _failed(
        message: str,
        *,
        code: str = "GRS-BAT-008",
    ) -> EmbeddingGenerationResult:
        return EmbeddingGenerationResult(
            status="failed",
            error_code=code,
            error_message=message,
        )


def build_scaffold_adapter(
    *,
    force_fail: bool = False,
) -> ScaffoldItemEmbeddingAdapter:
    return ScaffoldItemEmbeddingAdapter(force_fail=force_fail)
