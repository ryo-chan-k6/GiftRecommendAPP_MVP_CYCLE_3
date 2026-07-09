"""Popularity Score 算出ロジック（MOD-RECO-017 §8.3）。"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from reco.application.context_scorer.models import ContextScoreResult

from .constants import (
    DEFAULT_W_RATING,
    DEFAULT_W_REVIEW_COUNT,
    GUARD_CLIP_MAX,
    GUARD_CLIP_MIN,
    NEUTRAL_RATING_SCORE,
    NEUTRAL_REVIEW_COUNT_SCORE,
    POPULARITY_FORMULA_DEFAULT,
    POPULARITY_FORMULA_RATING_REVIEW_COUNT_WEIGHTED,
    POPULARITY_SCORE_DECIMAL_PLACES,
    RATING_CLIP_MAX,
    RATING_CLIP_MIN,
    RATING_SCALE,
)
from .errors import PopularityScorerError
from .models import (
    ItemReviewSummary,
    PopularityScoreEntry,
    PopularityScoreResult,
    PopularityScorerRunMetrics,
    PopularityWeights,
)
from .ports import ItemReviewSummaryRepositoryPort

if TYPE_CHECKING:
    pass


def guard_clip(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


def round_to_scale(value: float, decimal_places: int) -> float:
    return round(value, decimal_places)


def run_popularity_scoring(
    *,
    context_score_result: ContextScoreResult,
    config_versions: dict[str, str],
    review_summary_repository: ItemReviewSummaryRepositoryPort,
) -> tuple[PopularityScoreResult, PopularityScorerRunMetrics]:
    """context_score_result と item_review_summary から popularity_score を算出する。"""
    if not context_score_result.entries:
        empty = PopularityScoreResult(
            entries=(),
            max_review_count_in_candidates=0,
            total_scored=0,
        )
        metrics = PopularityScorerRunMetrics(
            popularity_scorer_candidate_count=0,
            popularity_scorer_latency_ms=0,
            popularity_missing_signal_count=0,
            popularity_score_value_out_of_range_count=0,
        )
        return empty, metrics

    formula = _resolve_popularity_formula(config_versions)
    if formula != POPULARITY_FORMULA_RATING_REVIEW_COUNT_WEIGHTED:
        raise PopularityScorerError(f"unsupported popularity_formula: {formula}")

    weights = _resolve_popularity_weights(config_versions)
    ranking_config_id = config_versions.get("ranking_config_id", "")

    item_ids = tuple(entry.item_id for entry in context_score_result.entries)
    review_map = review_summary_repository.fetch_review_summaries(item_ids)
    max_review_count = _derive_max_review_count(item_ids, review_map)

    scored_entries: list[PopularityScoreEntry] = []
    missing_signal_count = 0
    out_of_range_count = 0
    calculated_at = datetime.now(UTC)

    for entry in context_score_result.entries:
        summary = review_map.get(entry.item_id)
        (
            popularity_score,
            rating_score,
            review_count_score,
            review_average_used,
            review_count_used,
            signal_missing,
            entry_out_of_range,
        ) = _calculate_entry_score(
            summary=summary,
            max_review_count=max_review_count,
            weights=weights,
        )
        if signal_missing:
            missing_signal_count += 1
        out_of_range_count += entry_out_of_range

        scored_entries.append(
            PopularityScoreEntry(
                item_id=entry.item_id,
                popularity_score=popularity_score,
                popularity_formula=formula,
                calculated_at=calculated_at,
                ranking_config_id=ranking_config_id,
                signal_missing=signal_missing,
                rating_score=rating_score,
                review_count_score=review_count_score,
                review_average_used=review_average_used,
                review_count_used=review_count_used,
            ),
        )

    if context_score_result.total_scored != len(context_score_result.entries):
        raise PopularityScorerError(
            "context_score_result.total_scored is inconsistent with entries length",
        )

    result = PopularityScoreResult(
        entries=tuple(scored_entries),
        max_review_count_in_candidates=max_review_count,
        total_scored=len(scored_entries),
    )
    metrics = PopularityScorerRunMetrics(
        popularity_scorer_candidate_count=len(scored_entries),
        popularity_scorer_latency_ms=0,
        popularity_missing_signal_count=missing_signal_count,
        popularity_score_value_out_of_range_count=out_of_range_count,
    )
    return result, metrics


def _resolve_popularity_formula(config_versions: dict[str, str]) -> str:
    formula = config_versions.get("popularity_formula")
    if not formula:
        return POPULARITY_FORMULA_DEFAULT
    return formula


def _resolve_popularity_weights(config_versions: dict[str, str]) -> PopularityWeights:
    w_rating = _parse_optional_float(
        config_versions.get("popularity_weights.rating"),
        default=DEFAULT_W_RATING,
    )
    w_review_count = _parse_optional_float(
        config_versions.get("popularity_weights.review_count"),
        default=DEFAULT_W_REVIEW_COUNT,
    )
    return PopularityWeights(w_rating=w_rating, w_review_count=w_review_count)


def _parse_optional_float(raw: str | None, *, default: float) -> float:
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise PopularityScorerError(
            f"invalid popularity weight value: {raw}",
        ) from exc


def _derive_max_review_count(
    item_ids: tuple[str, ...],
    review_map: dict[str, ItemReviewSummary],
) -> int:
    max_count = 0
    for item_id in item_ids:
        summary = review_map.get(item_id)
        if summary is None:
            continue
        review_count = summary.review_count
        if review_count is None:
            continue
        if review_count < 0:
            raise PopularityScorerError(
                f"review_count must be non-negative for item: {item_id}",
            )
        max_count = max(max_count, review_count)
    return max_count


def _calculate_entry_score(
    *,
    summary: ItemReviewSummary | None,
    max_review_count: int,
    weights: PopularityWeights,
) -> tuple[float, float, float, float | None, int, bool, int]:
    signal_missing = summary is None
    out_of_range_count = 0

    if summary is None:
        review_average = None
        review_count = 0
    else:
        review_average = summary.review_average
        review_count = summary.review_count if summary.review_count is not None else 0
        if summary.review_count is not None and summary.review_count < 0:
            raise PopularityScorerError("review_count must be non-negative")

    if review_average is None:
        rating_score = NEUTRAL_RATING_SCORE
        review_average_used: float | None = None
        if summary is not None:
            signal_missing = True
    else:
        clipped_rating, rating_clip = _clip_rating(review_average)
        out_of_range_count += rating_clip
        rating_score = clipped_rating / RATING_SCALE
        review_average_used = clipped_rating

    if max_review_count <= 0:
        review_count_score = NEUTRAL_REVIEW_COUNT_SCORE
    else:
        review_count_score = math.log1p(review_count) / math.log1p(max_review_count)

    popularity_score = (
        weights.w_rating * rating_score + weights.w_review_count * review_count_score
    )
    clipped_score = guard_clip(popularity_score, GUARD_CLIP_MIN, GUARD_CLIP_MAX)
    final_score = round_to_scale(clipped_score, POPULARITY_SCORE_DECIMAL_PLACES)

    return (
        final_score,
        round_to_scale(rating_score, POPULARITY_SCORE_DECIMAL_PLACES),
        round_to_scale(review_count_score, POPULARITY_SCORE_DECIMAL_PLACES),
        review_average_used,
        review_count,
        signal_missing,
        out_of_range_count,
    )


def _clip_rating(review_average: float) -> tuple[float, int]:
    if review_average < RATING_CLIP_MIN or review_average > RATING_CLIP_MAX:
        return guard_clip(review_average, RATING_CLIP_MIN, RATING_CLIP_MAX), 1
    return review_average, 0
