"""Feature 正規化ロジック。"""

from enum import Enum
from typing import Iterable, Mapping

from gift_recommendation.shared_logic.catalog import load_mvp_feature_codes
from gift_recommendation.shared_logic.feature_engine import (
    clip_feature_vector,
    validate_complete_feature_vector,
)
from gift_recommendation.shared_logic.types import FeatureVector


class NormalizationMethod(str, Enum):
    """MVP 正規化方式。詳細パラメータは feature_normalization_version 側で管理する。"""

    RULE_BASED_CLIP = "rule_based_clip"


def normalize_features(
    raw_vector: Mapping[str, float],
    *,
    method: NormalizationMethod = NormalizationMethod.RULE_BASED_CLIP,
    feature_codes: Iterable[str] | None = None,
) -> dict[str, float]:
    """raw Feature を正規化 Feature へ変換する。"""
    codes = tuple(feature_codes) if feature_codes is not None else load_mvp_feature_codes()
    validate_complete_feature_vector(raw_vector, feature_codes=codes)

    if method is NormalizationMethod.RULE_BASED_CLIP:
        return clip_feature_vector(raw_vector, feature_codes=codes)

    raise ValueError(f"unsupported normalization method: {method}")
