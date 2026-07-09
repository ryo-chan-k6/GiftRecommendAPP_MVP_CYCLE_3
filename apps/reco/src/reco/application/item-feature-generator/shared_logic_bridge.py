"""Bridge to packages/shared-logic Feature Engine (§8.3.6)."""

from __future__ import annotations

import math
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path

from reco.domain.gift_meaning.features import (
    FEATURE_VALUE_MAX,
    FEATURE_VALUE_MIN,
    MVP_FEATURE_CODES,
)

from .errors import ItemFeatureGeneratorError


def _ensure_shared_logic_src_on_path() -> None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "packages" / "shared-logic" / "src"
        if candidate.is_dir():
            candidate_str = str(candidate)
            if candidate_str not in sys.path:
                sys.path.insert(0, candidate_str)
            return


def _try_import_shared_logic_engine() -> tuple[object, object] | None:
    _ensure_shared_logic_src_on_path()
    try:
        from gift_recommendation.shared_logic.feature_engine import (  # type: ignore[import-untyped]
            clip_feature_vector as shared_clip_feature_vector,
            integrate_feature_deltas as shared_integrate_feature_deltas,
        )
    except ModuleNotFoundError:
        return None
    return shared_integrate_feature_deltas, shared_clip_feature_vector


_SHARED_LOGIC_ENGINE = _try_import_shared_logic_engine()


def _resolve_feature_codes(
    feature_codes: Iterable[str] | None,
) -> tuple[str, ...]:
    if feature_codes is None:
        return MVP_FEATURE_CODES
    return tuple(feature_codes)


def _local_clip_feature_value(value: float) -> float:
    return max(FEATURE_VALUE_MIN, min(FEATURE_VALUE_MAX, value))


def _local_integrate_feature_deltas(
    base: Mapping[str, float],
    deltas: Mapping[str, float],
    *,
    feature_codes: Iterable[str] | None = None,
) -> dict[str, float]:
    codes = _resolve_feature_codes(feature_codes)
    merged: dict[str, float] = {code: float(base.get(code, 0.0)) for code in codes}
    for code, delta in deltas.items():
        if code not in merged:
            continue
        merged[code] = merged[code] + float(delta)
    return merged


def _local_clip_feature_vector(
    vector: Mapping[str, float],
    *,
    feature_codes: Iterable[str] | None = None,
) -> dict[str, float]:
    codes = _resolve_feature_codes(feature_codes)
    return {code: _local_clip_feature_value(vector[code]) for code in codes if code in vector}


def integrate_feature_deltas(
    base: Mapping[str, float],
    deltas: Mapping[str, float],
    *,
    feature_codes: Iterable[str] | None = None,
) -> dict[str, float]:
    if _SHARED_LOGIC_ENGINE is not None:
        shared_integrate, _ = _SHARED_LOGIC_ENGINE
        return shared_integrate(base, deltas, feature_codes=feature_codes)
    return _local_integrate_feature_deltas(base, deltas, feature_codes=feature_codes)


def clip_feature_vector(
    vector: Mapping[str, float],
    *,
    feature_codes: Iterable[str] | None = None,
) -> dict[str, float]:
    clipped = (
        _SHARED_LOGIC_ENGINE[1](vector, feature_codes=feature_codes)
        if _SHARED_LOGIC_ENGINE is not None
        else _local_clip_feature_vector(vector, feature_codes=feature_codes)
    )
    for axis, value in clipped.items():
        if math.isnan(value) or math.isinf(value):
            raise ItemFeatureGeneratorError(
                f"non-finite clipped feature value for axis {axis}",
            )
    return clipped
