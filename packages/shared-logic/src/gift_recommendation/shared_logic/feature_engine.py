"""Feature Engine: delta 統合と値域クリップ。"""

from typing import Iterable, Mapping

from gift_recommendation.shared_logic.catalog import load_mvp_feature_codes
from gift_recommendation.shared_logic.constants import FEATURE_VALUE_MAX, FEATURE_VALUE_MIN
from gift_recommendation.shared_logic.errors import IncompleteFeatureVectorError
from gift_recommendation.shared_logic.types import FeatureVector


def _resolve_feature_codes(
    feature_codes: Iterable[str] | None,
) -> tuple[str, ...]:
    if feature_codes is None:
        return load_mvp_feature_codes()
    return tuple(feature_codes)


def clip_feature_value(value: float) -> float:
    """Feature 値を 0.0〜1.0 に収める。"""
    return max(FEATURE_VALUE_MIN, min(FEATURE_VALUE_MAX, value))


def clip_feature_vector(
    vector: Mapping[str, float],
    *,
    feature_codes: Iterable[str] | None = None,
) -> dict[str, float]:
    codes = _resolve_feature_codes(feature_codes)
    return {code: clip_feature_value(vector[code]) for code in codes if code in vector}


def integrate_feature_deltas(
    base: Mapping[str, float],
    deltas: Mapping[str, float],
    *,
    feature_codes: Iterable[str] | None = None,
) -> dict[str, float]:
    """base Feature に delta を加算し、MVP 8 軸を返す（未指定軸は base または 0）。"""
    codes = _resolve_feature_codes(feature_codes)
    merged: dict[str, float] = {code: float(base.get(code, 0.0)) for code in codes}

    for code, delta in deltas.items():
        if code not in merged:
            continue
        merged[code] = merged[code] + float(delta)

    return merged


def validate_complete_feature_vector(
    vector: Mapping[str, float],
    *,
    feature_codes: Iterable[str] | None = None,
) -> FeatureVector:
    """MVP 8 軸がすべて非 None 相当で存在することを検証する。"""
    codes = _resolve_feature_codes(feature_codes)
    missing = tuple(code for code in codes if code not in vector)
    if missing:
        raise IncompleteFeatureVectorError(missing)
    return vector
