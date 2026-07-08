"""Final Score 算出ロジック（MOD-RECO-019 §8.3）。"""

from __future__ import annotations

from datetime import UTC, datetime

from reco.application.context_scorer.models import ContextScoreResult
from reco.application.popularity_scorer.models import PopularityScoreResult
from reco.application.risk_scorer.models import RiskPenaltyResult

from .constants import (
    DEFAULT_DIVERSITY_PENALTY,
    DEFAULT_POPULARITY_SCORE_MISSING,
    DEFAULT_RISK_PENALTY_MISSING,
    DEFAULT_W_CONTEXT,
    DEFAULT_W_POPULARITY,
    DEFAULT_W_RISK,
    FINAL_SCORE_DECIMAL_PLACES,
    FINAL_SCORE_FORMULA_DEFAULT,
    FINAL_SCORE_FORMULA_LINEAR_WEIGHTED_V1,
    GUARD_CLIP_MAX,
    GUARD_CLIP_MIN,
    WEIGHT_SUM_TOLERANCE,
)
from .errors import FinalScoreCalculatorError
from .models import (
    FinalScoreCalculatorRunMetrics,
    FinalScoreEntry,
    FinalScoreResult,
    RankingWeightsUsed,
)


def guard_clip(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


def round_to_scale(value: float, decimal_places: int) -> float:
    return round(value, decimal_places)


def run_final_score_calculation(
    *,
    risk_penalty_result: RiskPenaltyResult,
    context_score_result: ContextScoreResult,
    popularity_score_result: PopularityScoreResult,
    config_versions: dict[str, str],
) -> tuple[FinalScoreResult, FinalScoreCalculatorRunMetrics]:
    """3 系統スコアから pre_rank_score / final_score を算出する。"""
    if not risk_penalty_result.entries:
        empty = FinalScoreResult(entries=(), total_scored=0)
        metrics = FinalScoreCalculatorRunMetrics(
            final_score_calculator_candidate_count=0,
            final_score_calculator_latency_ms=0,
            final_score_excluded_candidate_count=0,
            final_score_value_out_of_range_count=0,
        )
        return empty, metrics

    formula = _resolve_final_score_formula(config_versions)
    if formula != FINAL_SCORE_FORMULA_LINEAR_WEIGHTED_V1:
        raise FinalScoreCalculatorError(f"unsupported final_score_formula: {formula}")

    weights = _resolve_ranking_weights(config_versions)
    ranking_config_id = config_versions.get("ranking_config_id", "")

    context_map = {entry.item_id: entry for entry in context_score_result.entries}
    popularity_map = {
        entry.item_id: entry for entry in popularity_score_result.entries
    }

    scored_entries: list[FinalScoreEntry] = []
    excluded_count = 0
    out_of_range_count = 0
    calculated_at = datetime.now(UTC)

    for risk_entry in risk_penalty_result.entries:
        item_id = risk_entry.item_id

        context_entry = context_map.get(item_id)
        if context_entry is None:
            raise FinalScoreCalculatorError(
                f"context_score_result missing item_id for final score: {item_id}",
            )

        context_score = context_entry.context_score
        if context_score is None:
            excluded_count += 1
            continue

        popularity_entry = popularity_map.get(item_id)
        if popularity_entry is None:
            raise FinalScoreCalculatorError(
                f"popularity_score_result missing item_id for final score: {item_id}",
            )

        popularity_score = popularity_entry.popularity_score
        popularity_missing = popularity_score is None
        if popularity_missing:
            popularity_score = DEFAULT_POPULARITY_SCORE_MISSING

        risk_penalty = risk_entry.risk_penalty
        if risk_penalty is None:
            risk_penalty = DEFAULT_RISK_PENALTY_MISSING

        (
            clipped_context,
            clipped_popularity,
            clipped_risk,
            entry_out_of_range,
        ) = _clip_input_scores(context_score, popularity_score, risk_penalty)
        out_of_range_count += entry_out_of_range

        context_contribution = weights.w_context * clipped_context
        popularity_contribution = weights.w_popularity * clipped_popularity
        risk_contribution = -weights.w_risk * clipped_risk

        raw_pre_rank = (
            context_contribution + popularity_contribution + risk_contribution
        )
        clipped_pre_rank = guard_clip(raw_pre_rank, GUARD_CLIP_MIN, GUARD_CLIP_MAX)
        if clipped_pre_rank != raw_pre_rank:
            out_of_range_count += 1

        diversity_penalty = DEFAULT_DIVERSITY_PENALTY
        raw_final = clipped_pre_rank - diversity_penalty
        clipped_final = guard_clip(raw_final, GUARD_CLIP_MIN, GUARD_CLIP_MAX)
        if clipped_final != raw_final:
            out_of_range_count += 1

        pre_rank_score = round_to_scale(clipped_pre_rank, FINAL_SCORE_DECIMAL_PLACES)
        final_score = round_to_scale(clipped_final, FINAL_SCORE_DECIMAL_PLACES)
        score_breakdown = _build_score_breakdown(
            context_score=clipped_context,
            popularity_score=clipped_popularity,
            risk_penalty=clipped_risk,
            weights=weights,
            context_contribution=context_contribution,
            popularity_contribution=popularity_contribution,
            risk_contribution=risk_contribution,
            pre_rank_score=pre_rank_score,
            final_score=final_score,
        )

        scored_entries.append(
            FinalScoreEntry(
                item_id=item_id,
                context_score=round_to_scale(clipped_context, FINAL_SCORE_DECIMAL_PLACES),
                popularity_score=round_to_scale(
                    clipped_popularity,
                    FINAL_SCORE_DECIMAL_PLACES,
                ),
                risk_penalty=round_to_scale(clipped_risk, FINAL_SCORE_DECIMAL_PLACES),
                pre_rank_score=pre_rank_score,
                diversity_penalty=diversity_penalty,
                final_score=final_score,
                score_breakdown=score_breakdown,
                final_score_formula=formula,
                ranking_weights_used=weights,
                calculated_at=calculated_at,
                ranking_config_id=ranking_config_id,
            ),
        )

    result = FinalScoreResult(
        entries=tuple(scored_entries),
        total_scored=len(scored_entries),
    )
    metrics = FinalScoreCalculatorRunMetrics(
        final_score_calculator_candidate_count=len(scored_entries),
        final_score_calculator_latency_ms=0,
        final_score_excluded_candidate_count=excluded_count,
        final_score_value_out_of_range_count=out_of_range_count,
    )
    return result, metrics


def _resolve_final_score_formula(config_versions: dict[str, str]) -> str:
    formula = config_versions.get("final_score_formula")
    if not formula:
        return FINAL_SCORE_FORMULA_DEFAULT
    return formula


def _resolve_ranking_weights(config_versions: dict[str, str]) -> RankingWeightsUsed:
    raw_weights = RankingWeightsUsed(
        w_context=_parse_optional_float(
            config_versions.get("ranking_weights.context"),
            default=DEFAULT_W_CONTEXT,
        ),
        w_popularity=_parse_optional_float(
            config_versions.get("ranking_weights.popularity"),
            default=DEFAULT_W_POPULARITY,
        ),
        w_risk=_parse_optional_float(
            config_versions.get("ranking_weights.risk"),
            default=DEFAULT_W_RISK,
        ),
    )
    return _normalize_ranking_weights(raw_weights)


def _normalize_ranking_weights(weights: RankingWeightsUsed) -> RankingWeightsUsed:
    total = weights.w_context + weights.w_popularity + weights.w_risk
    if total <= 0.0:
        raise FinalScoreCalculatorError(
            "ranking_weights sum must be positive",
        )

    if abs(total - 1.0) <= WEIGHT_SUM_TOLERANCE:
        return weights

    return RankingWeightsUsed(
        w_context=weights.w_context / total,
        w_popularity=weights.w_popularity / total,
        w_risk=weights.w_risk / total,
    )


def _parse_optional_float(raw: str | None, *, default: float) -> float:
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise FinalScoreCalculatorError(
            f"invalid final score config value: {raw}",
        ) from exc


def _clip_input_scores(
    context_score: float,
    popularity_score: float,
    risk_penalty: float,
) -> tuple[float, float, float, int]:
    out_of_range_count = 0
    clipped_context, context_clip = _clip_unit_value(context_score)
    clipped_popularity, popularity_clip = _clip_unit_value(popularity_score)
    clipped_risk, risk_clip = _clip_unit_value(risk_penalty)
    out_of_range_count += context_clip + popularity_clip + risk_clip
    return clipped_context, clipped_popularity, clipped_risk, out_of_range_count


def _clip_unit_value(value: float) -> tuple[float, int]:
    if value < GUARD_CLIP_MIN or value > GUARD_CLIP_MAX:
        return guard_clip(value, GUARD_CLIP_MIN, GUARD_CLIP_MAX), 1
    return value, 0


def _build_score_breakdown(
    *,
    context_score: float,
    popularity_score: float,
    risk_penalty: float,
    weights: RankingWeightsUsed,
    context_contribution: float,
    popularity_contribution: float,
    risk_contribution: float,
    pre_rank_score: float,
    final_score: float,
) -> dict[str, object]:
    return {
        "context": {
            "score": round_to_scale(context_score, FINAL_SCORE_DECIMAL_PLACES),
            "weight": weights.w_context,
            "contribution": round_to_scale(context_contribution, FINAL_SCORE_DECIMAL_PLACES),
        },
        "popularity": {
            "score": round_to_scale(popularity_score, FINAL_SCORE_DECIMAL_PLACES),
            "weight": weights.w_popularity,
            "contribution": round_to_scale(
                popularity_contribution,
                FINAL_SCORE_DECIMAL_PLACES,
            ),
        },
        "risk": {
            "penalty": round_to_scale(risk_penalty, FINAL_SCORE_DECIMAL_PLACES),
            "weight": weights.w_risk,
            "contribution": round_to_scale(risk_contribution, FINAL_SCORE_DECIMAL_PLACES),
        },
        "diversity": {
            "penalty": DEFAULT_DIVERSITY_PENALTY,
        },
        "pre_rank_score": pre_rank_score,
        "final_score": final_score,
    }
