"""Context Score 算出ロジック（MOD-RECO-016 §8.3）。"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from reco.application.meaning_match_aggregator.models import (
    MeaningMatchEntry,
    MeaningMatchResult,
)

from .constants import (
    CONTEXT_SCORE_DECIMAL_PLACES,
    CONTEXT_SCORE_FORMULA_DEFAULT,
    CONTEXT_SCORE_FORMULA_LAMBDA_CTX_WEIGHTED,
    GUARD_CLIP_MAX,
    GUARD_CLIP_MIN,
    LAMBDA_CTX_FALLBACK,
)
from .errors import ContextScorerError
from .models import ContextScoreEntry, ContextScoreResult, ContextScorerRunMetrics

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


def guard_clip(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


def round_to_scale(value: float, decimal_places: int) -> float:
    return round(value, decimal_places)


def run_context_scoring(
    *,
    meaning_match_result: MeaningMatchResult,
    config_versions: dict[str, str],
    context: ExecutionContext,
) -> tuple[ContextScoreResult, ContextScorerRunMetrics, str | None]:
    """meaning_match_result と lambda_ctx から context_score を算出する。"""
    if not meaning_match_result.entries:
        empty = ContextScoreResult(
            entries=(),
            lambda_ctx_applied=LAMBDA_CTX_FALLBACK,
            total_scored=0,
        )
        metrics = ContextScorerRunMetrics(
            context_scorer_candidate_count=0,
            context_scorer_latency_ms=0,
            context_score_value_out_of_range_count=0,
            lambda_ctx_applied=LAMBDA_CTX_FALLBACK,
        )
        return empty, metrics, None

    formula = _resolve_context_score_formula(config_versions)
    if formula != CONTEXT_SCORE_FORMULA_LAMBDA_CTX_WEIGHTED:
        raise ContextScorerError(
            f"unsupported context_score_formula: {formula}",
        )

    raw_lambda_ctx, warning_code = _resolve_lambda_ctx_raw(context)
    lambda_ctx_applied, lambda_clip_count = _finalize_lambda_ctx(raw_lambda_ctx)

    out_of_range_count = lambda_clip_count
    scored_entries: list[ContextScoreEntry] = []
    calculated_at = datetime.now(UTC)

    for entry in meaning_match_result.entries:
        _validate_meaning_match_entry(entry)
        social_match, social_clip = _clip_match(entry.social_match)
        symbolic_match, symbolic_clip = _clip_match(entry.symbolic_match)
        out_of_range_count += social_clip + symbolic_clip

        context_score = _calculate_lambda_ctx_weighted_score(
            social_match=social_match,
            symbolic_match=symbolic_match,
            lambda_ctx=lambda_ctx_applied,
        )

        scored_entries.append(
            ContextScoreEntry(
                item_id=entry.item_id,
                context_score=context_score,
                context_score_formula=formula,
                calculated_at=calculated_at,
                matching_config_id=entry.matching_config_id,
            ),
        )

    if meaning_match_result.total_aggregated != len(meaning_match_result.entries):
        raise ContextScorerError(
            "meaning_match_result.total_aggregated is inconsistent with entries length",
        )

    result = ContextScoreResult(
        entries=tuple(scored_entries),
        lambda_ctx_applied=lambda_ctx_applied,
        total_scored=len(scored_entries),
    )
    metrics = ContextScorerRunMetrics(
        context_scorer_candidate_count=len(scored_entries),
        context_scorer_latency_ms=0,
        context_score_value_out_of_range_count=out_of_range_count,
        lambda_ctx_applied=lambda_ctx_applied,
    )
    return result, metrics, warning_code


def _resolve_context_score_formula(config_versions: dict[str, str]) -> str:
    formula = config_versions.get("context_score_formula")
    if not formula:
        return CONTEXT_SCORE_FORMULA_DEFAULT
    return formula


def _resolve_lambda_ctx_raw(context: ExecutionContext) -> tuple[float, str | None]:
    user_meaning = context.user_meaning
    if user_meaning is not None:
        raw = getattr(user_meaning, "lambda_ctx", None)
        if raw is not None:
            return raw, None

    user_context = context.user_context
    if user_context is not None:
        return user_context.lambda_ctx, "user_meaning_lambda_ctx_missing"

    return LAMBDA_CTX_FALLBACK, "lambda_ctx_both_missing"


def _finalize_lambda_ctx(raw_value: float) -> tuple[float, int]:
    if math.isnan(raw_value) or math.isinf(raw_value):
        raise ContextScorerError("lambda_ctx is non-finite")
    clip_count = 0
    if raw_value < GUARD_CLIP_MIN or raw_value > GUARD_CLIP_MAX:
        clip_count = 1
    clipped = guard_clip(raw_value, GUARD_CLIP_MIN, GUARD_CLIP_MAX)
    return round_to_scale(clipped, CONTEXT_SCORE_DECIMAL_PLACES), clip_count


def _validate_meaning_match_entry(entry: MeaningMatchEntry) -> None:
    if entry.social_match is None:
        raise ContextScorerError(
            f"social_match is required for item: {entry.item_id}",
        )
    if entry.symbolic_match is None:
        raise ContextScorerError(
            f"symbolic_match is required for item: {entry.item_id}",
        )


def _clip_match(value: float) -> tuple[float, int]:
    if value < GUARD_CLIP_MIN:
        return GUARD_CLIP_MIN, 1
    if value > GUARD_CLIP_MAX:
        return GUARD_CLIP_MAX, 1
    return value, 0


def _calculate_lambda_ctx_weighted_score(
    *,
    social_match: float,
    symbolic_match: float,
    lambda_ctx: float,
) -> float:
    context_score = (1.0 - lambda_ctx) * social_match + lambda_ctx * symbolic_match
    clipped = guard_clip(context_score, GUARD_CLIP_MIN, GUARD_CLIP_MAX)
    return round_to_scale(clipped, CONTEXT_SCORE_DECIMAL_PLACES)
