"""lambda_ctx resolution for MOD-RECO-009."""

from __future__ import annotations

import math

from .constants import (
    GUARD_CLIP_MAX,
    GUARD_CLIP_MIN,
    LAMBDA_CTX_DECIMAL_PLACES,
    LAMBDA_CTX_FALLBACK,
)
from .errors import UserContextBuildError
from .ports import LambdaContextRuleRepositoryPort


def guard_clip(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


def round_to_scale(value: float, decimal_places: int) -> float:
    return round(value, decimal_places)


def finalize_lambda_ctx(raw_value: float) -> float:
    if math.isnan(raw_value) or math.isinf(raw_value):
        raise UserContextBuildError("lambda_ctx is non-finite")
    clipped = guard_clip(raw_value, GUARD_CLIP_MIN, GUARD_CLIP_MAX)
    return round_to_scale(clipped, LAMBDA_CTX_DECIMAL_PLACES)


def resolve_lambda_ctx(
    *,
    semantic_config_version_id: str,
    relationship_code: str,
    occasion_code: str,
    rule_repository: LambdaContextRuleRepositoryPort,
) -> tuple[float, bool]:
    """Return (lambda_ctx, used_fallback). Rule 未設定時は 0.5 固定 + fallback=True."""
    rule_value = rule_repository.get_lambda_ctx(
        semantic_config_version_id,
        relationship_code,
        occasion_code,
    )
    if rule_value is None:
        return finalize_lambda_ctx(LAMBDA_CTX_FALLBACK), True
    return finalize_lambda_ctx(rule_value), False
