"""IF-SHARED-001 Item Semantic 生成アダプタ（in-process / MVP Scaffold）.

仕様書 §8.3 / §18.1 No.3–4:
- in-process Python package 呼び出し（Reco Hosting HTTP ではない）
- MVP 初版 LLM は Scaffold（Rule-first / LLM スタブ）。実 LLM は後続 Human
- MOD-RECO-026 相当の生成結果を返し、DB Upsert は batch（IF-DB-BATCH-011）が行う

apps/reco を変更せず、batch 内に Protocol 互換の Scaffold 実装を置く。
実 reco import は PYTHONPATH に apps/reco がある場合の任意拡張とし、
本 Task の CI / `--scaffold-demo` は ScaffoldAdapter を正とする。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from batch.application.item_semantic.models import (
    ItemSemanticRow,
    SemanticGenerationContext,
    SemanticGenerationResult,
)

ExistingLookup = Callable[[str, str], ItemSemanticRow | None]


def compute_semantic_input_hash(context: SemanticGenerationContext) -> str:
    """MOD-RECO-026 §8.3.6 相当。item_review は hash 対象外。"""

    def _norm(value: str | None) -> str:
        return "" if value is None else value.strip()

    payload = {
        "item_id": context.item_id,
        "item_name": _norm(context.item_name),
        "item_caption": _norm(context.item_caption),
        "item_description": _norm(context.item_description),
        "genre_name": _norm(context.genre_name),
        "attributes": sorted(v.strip() for v in context.attributes if v.strip()),
        "tags": sorted(v.strip() for v in context.tags if v.strip()),
        "semantic_config_version_id": context.semantic_config_version_id,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ItemSemanticGeneratorPort(Protocol):
    """IF-SHARED-001 Port（MOD-RECO-026 Batch-facing）。"""

    def generate_item_semantic(
        self,
        context: SemanticGenerationContext,
    ) -> SemanticGenerationResult: ...


@dataclass
class ScaffoldItemSemanticAdapter:
    """MVP Scaffold アダプタ: Rule-first スタブ / LLM 非呼出 / Upsert 非実施."""

    find_existing: ExistingLookup
    force_fail: bool = False

    def generate_item_semantic(
        self,
        context: SemanticGenerationContext,
    ) -> SemanticGenerationResult:
        if not context.trace_id.strip():
            return SemanticGenerationResult(
                status="failed",
                error_code="GRS-BAT-008",
                error_message="trace_id is required",
            )
        if not context.item_id.strip() or not context.semantic_config_version_id.strip():
            return SemanticGenerationResult(
                status="failed",
                error_code="GRS-BAT-008",
                error_message="item_id / semantic_config_version_id required",
            )
        if self.force_fail:
            return SemanticGenerationResult(
                status="failed",
                error_code="GRS-BAT-008",
                error_message="scaffold forced failure",
            )

        input_hash = compute_semantic_input_hash(context)
        if context.skip_if_unchanged:
            existing = self.find_existing(context.item_id, context.semantic_config_version_id)
            if existing is not None and existing.semantic_input_hash == input_hash:
                return SemanticGenerationResult(
                    status="skipped",
                    semantic_json=dict(existing.semantic_json),
                    item_semantic_id=existing.item_semantic_id,
                    skip_reason="semantic_input_unchanged",
                    semantic_input_hash=input_hash,
                )

        # Scaffold Rule-first: テキストが空でも concepts: [] で generated 可（§9.3）
        concepts: list[dict[str, object]] = []
        name = (context.item_name or "").strip()
        if name:
            concepts.append(
                {
                    "concept_code": "scaffold_named_item",
                    "confidence": 0.5,
                    "extraction_method": "keyword",
                    "source_span": name[:64],
                }
            )

        return SemanticGenerationResult(
            status="generated",
            semantic_json={"concepts": concepts},
            semantic_input_hash=input_hash,
        )


def build_scaffold_adapter(*, find_existing: ExistingLookup) -> ScaffoldItemSemanticAdapter:
    return ScaffoldItemSemanticAdapter(find_existing=find_existing)
