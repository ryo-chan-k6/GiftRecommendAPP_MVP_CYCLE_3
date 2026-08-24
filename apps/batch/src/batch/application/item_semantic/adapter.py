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

# MVP 18 Concept（semantic_concept seed / Featureルール正本）
MVP_CONCEPT_CODES: tuple[str, ...] = (
    "formal_refined",
    "safe_classic",
    "prestigious_quality",
    "practical_useful",
    "emotional_warm",
    "special_memorable",
    "surprising_unique",
    "romantic_affectionate",
    "close_personal",
    "symbolic_identity_fit",
    "story_narrative",
    "stylish_aesthetic",
    "cute_soft",
    "casual_light",
    "not_too_much",
    "not_too_safe",
    "luxurious_rich",
    "cheerful_positive",
)

# Semanticルール定義書 §12 系の最小 keyword → concept（interim Rule-first）
_KEYWORD_CONCEPTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("高級", "上質", "プレミアム", "贈答"), "prestigious_quality"),
    (("実用", "便利", "普段使い", "機能的"), "practical_useful"),
    (("かわいい", "可愛", "癒し", "ふんわり"), "cute_soft"),
    (("おしゃれ", "デザイン", "スタイリッシュ", "洗練"), "stylish_aesthetic"),
    (("ロマン", "愛情", "恋人"), "romantic_affectionate"),
    (("ユニーク", "意外", "珍しい"), "surprising_unique"),
    (("カジュアル", "気軽"), "casual_light"),
    (("豪華", "華やか"), "luxurious_rich"),
    (("明るい", "前向き", "ポジティブ"), "cheerful_positive"),
    (("ストーリー", "物語", "エピソード"), "story_narrative"),
    (("無難", "定番", "オーソドックス"), "safe_classic"),
    (("上品", "端正", "フォーマル"), "formal_refined"),
    (("温かい", "やさしい", "優しい"), "emotional_warm"),
    (("特別", "記念", "思い出"), "special_memorable"),
)


def pick_concepts_for_item(
    *,
    item_id: str,
    item_name: str | None,
    item_caption: str | None = None,
    item_description: str | None = None,
    genre_name: str | None = None,
    tags: tuple[str, ...] = (),
) -> list[dict[str, object]]:
    """Rule-first 最小抽出。keyword 優先、未ヒット時は item_id hash で 1 concept（interim）."""

    text_parts = [
        (item_name or "").strip(),
        (item_caption or "").strip(),
        (item_description or "").strip(),
        (genre_name or "").strip(),
        " ".join(t.strip() for t in tags if t.strip()),
    ]
    haystack = " ".join(p for p in text_parts if p)
    if not haystack:
        return []

    for keywords, concept_code in _KEYWORD_CONCEPTS:
        if any(keyword in haystack for keyword in keywords):
            return [
                {
                    "concept_code": concept_code,
                    "confidence": 0.6,
                    "extraction_method": "keyword",
                    "source_span": haystack[:64],
                }
            ]

    digest = hashlib.sha256(item_id.encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % len(MVP_CONCEPT_CODES)
    return [
        {
            "concept_code": MVP_CONCEPT_CODES[idx],
            "confidence": 0.4,
            "extraction_method": "scaffold_hash",
            "source_span": haystack[:64],
        }
    ]


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
        # concept_feature_rule に載る 18 Concept を出す（scaffold_named_item は使わない）
        concepts = pick_concepts_for_item(
            item_id=context.item_id,
            item_name=context.item_name,
            item_caption=context.item_caption,
            item_description=context.item_description,
            genre_name=context.genre_name,
            tags=tuple(context.tags),
        )

        return SemanticGenerationResult(
            status="generated",
            semantic_json={"concepts": concepts},
            semantic_input_hash=input_hash,
        )


def build_scaffold_adapter(*, find_existing: ExistingLookup) -> ScaffoldItemSemanticAdapter:
    return ScaffoldItemSemanticAdapter(find_existing=find_existing)
