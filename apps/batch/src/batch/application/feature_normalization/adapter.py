"""IF-SHARED-003 Feature正規化アダプタ（in-process / MVP Scaffold）.

仕様書 §8.3 / §9.2 / §18.1:
- in-process Python package 呼び出し（Reco Hosting HTTP ではない）
- MVP は固定パラメータ sigmoid（Featureルール定義書 §14.2/§14.3）。LLM は利用しない
- MOD-BATCH-034 相当。normalized 8 軸を返し、DB 反映は batch（IF-DB-BATCH-014）が行う
- raw_feature_value は変更しない（BATCH-012 責務）

apps/reco を変更せず、batch 内に Protocol 互換の Scaffold 実装を置く。
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Protocol

from batch.application.feature_normalization.models import (
    MeaningProjection,
    NormalizationResult,
    NormalizedAxisValue,
    NormalizeContext,
)

# MVP 8 軸（Featureルール定義書 固定名）
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

# Social / Symbolic 射影の軸割当（item_meaning §5.3 / GiftMeaningSpace §5–§7）
SOCIAL_FEATURE_CODES: tuple[str, ...] = (
    "formality",
    "safety",
    "brand_appropriateness",
)
SYMBOLIC_FEATURE_CODES: tuple[str, ...] = (
    "emotion",
    "novelty",
    "intimacy",
    "symbolic_identity",
    "story_richness",
)

# MVP scaffold 既定の現行 normalization version（skip / 冪等キー）
DEFAULT_NORMALIZATION_VERSION = "scaffold-feature-norm-v1"

# Featureルール定義書 §14.3 初期パラメータ
DEFAULT_CENTER_FEATURE = 0.5
DEFAULT_K_FEATURE = 4.0

_HEX64 = re.compile(r"^[0-9a-f]{64}$")

# 出力飽和とみなす境界（監視指標用。値域制御ではない）
_SATURATE_LOW = 0.01
_SATURATE_HIGH = 0.99


def sigmoid(value: float) -> float:
    """sigmoid(x) = 1 / (1 + exp(-x))（Featureルール定義書 §14.2）。"""

    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def normalize_sigmoid(raw_value: float, *, center: float, k: float) -> float:
    """normalized_value = sigmoid(k * (raw_value - center))。"""

    return sigmoid(k * (raw_value - center))


def is_valid_feature_input_hash(value: str | None) -> bool:
    """SHA-256 lowercase hex (64 chars) か検証。"""

    return bool(value) and bool(_HEX64.match(value or ""))


def _mean(values: tuple[float, ...]) -> float:
    return sum(values) / len(values) if values else 0.0


def project_item_meaning(
    normalized_by_code: dict[str, float],
) -> MeaningProjection | None:
    """normalized 8 軸を Social / Symbolic へ射影（MVP は単純平均）.

    item_meaning §5.3: 8 軸のいずれかが NULL の場合は UPSERT しない（None を返す）。
    重み正本は semantic_config_version（行に重み JSON を保持しない）。
    MVP は重み未設定＝単純平均。
    """

    for code in MVP_FEATURE_CODES:
        if code not in normalized_by_code:
            return None
    social = _mean(tuple(normalized_by_code[c] for c in SOCIAL_FEATURE_CODES))
    symbolic = _mean(tuple(normalized_by_code[c] for c in SYMBOLIC_FEATURE_CODES))
    return MeaningProjection(item_social=social, item_symbolic=symbolic)


class FeatureNormalizerPort(Protocol):
    """IF-SHARED-003 Port（MOD-BATCH-034 Batch-facing）。"""

    def normalize_features(self, context: NormalizeContext) -> NormalizationResult: ...


@dataclass
class ScaffoldFeatureNormalizerAdapter:
    """MVP Scaffold: 固定 sigmoid で raw 8 軸を normalized へ変換。LLM 非呼出 / DB 非反映."""

    force_fail: bool = False

    def normalize_features(self, context: NormalizeContext) -> NormalizationResult:
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

        raw_by_code = {axis.feature_code: axis for axis in context.raw_axes}
        for code in MVP_FEATURE_CODES:
            if code not in raw_by_code:
                return self._failed(f"raw feature missing: {code}", code="GRS-VAL-001")

        center = context.params.center_feature
        k = context.params.k_feature
        saturate = 0
        normalized: list[NormalizedAxisValue] = []
        for code in MVP_FEATURE_CODES:
            value = normalize_sigmoid(
                raw_by_code[code].raw_feature_value, center=center, k=k
            )
            if value <= _SATURATE_LOW or value >= _SATURATE_HIGH:
                saturate += 1
            normalized.append(
                NormalizedAxisValue(feature_code=code, normalized_feature_value=value)
            )

        return NormalizationResult(
            status="normalized",
            normalized=tuple(normalized),
            feature_normalization_version_id=context.feature_normalization_version_id,
            feature_input_hash=context.feature_input_hash,
            axis_count=len(normalized),
            saturate_count=saturate,
        )

    @staticmethod
    def _failed(message: str, *, code: str = "GRS-BAT-008") -> NormalizationResult:
        return NormalizationResult(
            status="failed",
            error_code=code,
            error_message=message,
        )


def build_scaffold_adapter(*, force_fail: bool = False) -> ScaffoldFeatureNormalizerAdapter:
    return ScaffoldFeatureNormalizerAdapter(force_fail=force_fail)
