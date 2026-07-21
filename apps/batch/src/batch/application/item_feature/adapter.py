"""IF-SHARED-002 Item Feature 生成アダプタ（in-process / MVP Scaffold）.

仕様書 §8.3 / §18.1 No.3–5:
- in-process Python package 呼び出し（Reco Hosting HTTP ではない）
- MVP はルールベース。LLM / Scaffold LLM は利用しない
- MOD-RECO-027 相当の raw 8 軸を返し、DB Upsert は batch（IF-DB-BATCH-013）が行う

apps/reco を変更せず、batch 内に Protocol 互換の Scaffold 実装を置く。
実 reco import は PYTHONPATH に apps/reco がある場合の任意拡張とし、
本 Task の CI / `--scaffold-demo` は ScaffoldAdapter を正とする。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from batch.application.item_feature.models import (
    FeatureAxisValue,
    FeatureGenerationContext,
    FeatureGenerationResult,
)

# MVP 8 軸（Feature定義書固定名）
MVP_FEATURE_CODES: tuple[str, ...] = (
    "formality",
    "safety",
    "brand_appropriateness",
    "emotion",
    "novelty",
    "intimacy",
    "symbolic_identity",
    "story_richness",
)

# MVP scaffold 既定の現行 normalization version（skip / 冪等キー）
DEFAULT_NORMALIZATION_VERSION = "scaffold-feature-norm-v1"

_RAW_BASELINE = 0.5
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

# concept_code -> {feature_code: delta}。MVP ルールベース最小辞書（apps/reco 非依存）。
ConceptFeatureRule = dict[str, dict[str, float]]


def clip_unit(value: float) -> tuple[float, bool]:
    """[0.0, 1.0] にクリップし、クリップ発生有無を返す。"""

    if value < 0.0:
        return 0.0, True
    if value > 1.0:
        return 1.0, True
    return value, False


def is_valid_feature_input_hash(value: str | None) -> bool:
    """SHA-256 lowercase hex (64 chars) か検証。"""

    return bool(value) and bool(_HEX64.match(value or ""))


class ItemFeatureGeneratorPort(Protocol):
    """IF-SHARED-002 Port（MOD-RECO-027 Batch-facing）。"""

    def generate_item_feature(
        self,
        context: FeatureGenerationContext,
    ) -> FeatureGenerationResult: ...


@dataclass
class ScaffoldItemFeatureAdapter:
    """MVP Scaffold アダプタ: ルールベース raw 8 軸生成 / LLM 非呼出 / Upsert 非実施."""

    concept_feature_rules: ConceptFeatureRule = field(default_factory=dict)
    force_fail: bool = False

    def generate_item_feature(
        self,
        context: FeatureGenerationContext,
    ) -> FeatureGenerationResult:
        if not context.trace_id.strip():
            return self._failed("trace_id is required")
        if not context.item_id.strip() or not context.semantic_config_version_id.strip():
            return self._failed("item_id / semantic_config_version_id required")
        if not is_valid_feature_input_hash(context.feature_input_hash):
            return self._failed("feature_input_hash must be 64 hex")
        if not context.feature_normalization_version_id.strip():
            return self._failed("feature_normalization_version_id required")
        if self.force_fail:
            return self._failed("scaffold forced failure")

        rule_hits = 0
        clip_count = 0
        features: list[FeatureAxisValue] = []
        for code in MVP_FEATURE_CODES:
            raw = _RAW_BASELINE
            for concept in context.concepts:
                delta = self.concept_feature_rules.get(concept.concept_code, {}).get(code)
                if delta is None:
                    continue
                rule_hits += 1
                raw += delta * concept.source_weight * concept.confidence
            clipped, was_clipped = clip_unit(raw)
            if was_clipped:
                clip_count += 1
            features.append(FeatureAxisValue(feature_code=code, raw_feature_value=clipped))

        return FeatureGenerationResult(
            status="generated",
            features=tuple(features),
            feature_normalization_version_id=context.feature_normalization_version_id,
            feature_input_hash=context.feature_input_hash,
            concept_count=len(context.concepts),
            rule_hit_count=rule_hits,
            raw_clip_count=clip_count,
        )

    @staticmethod
    def _failed(message: str) -> FeatureGenerationResult:
        return FeatureGenerationResult(
            status="failed",
            error_code="GRS-BAT-008",
            error_message=message,
        )


def build_scaffold_adapter(
    *,
    concept_feature_rules: ConceptFeatureRule | None = None,
    force_fail: bool = False,
) -> ScaffoldItemFeatureAdapter:
    return ScaffoldItemFeatureAdapter(
        concept_feature_rules=dict(concept_feature_rules or {}),
        force_fail=force_fail,
    )
