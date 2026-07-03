"""Final Ranker 選定ロジック（MOD-RECO-020 §8.3）。"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import UTC, datetime

from reco.application.feature_matcher.models import FeatureMatchEntry, FeatureMatchResult
from reco.application.final_score_calculator.models import FinalScoreEntry, FinalScoreResult
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES
from reco.domain.recommendation.request import RecommendationRequest

from .constants import (
    DEFAULT_DIVERSITY_METHOD,
    DEFAULT_LAMBDA_MMR,
    DEFAULT_MMR_CANDIDATE_LIMIT,
    DEFAULT_TOP_K_DEFAULT,
    LAMBDA_MMR_MAX,
    LAMBDA_MMR_MIN,
    SCORE_DECIMAL_PLACES,
    TOP_K_MAX,
    TOP_K_MIN,
)
from .errors import FinalRankerError
from .models import (
    FinalRankerRunMetrics,
    RankedItemEntry,
    RankedItems,
    RankingParams,
)


@dataclass(frozen=True)
class _CandidateState:
    entry: FinalScoreEntry
    mmr_score: float | None = None
    max_similarity_to_selected: float = 0.0


def round_to_scale(value: float, decimal_places: int) -> float:
    return round(value, decimal_places)


def run_final_ranking(
    *,
    final_score_result: FinalScoreResult,
    feature_match_result: FeatureMatchResult,
    recommendation_request: RecommendationRequest,
    config_versions: dict[str, str],
) -> tuple[RankedItems, FinalRankerRunMetrics]:
    """final_score_result から ranked_items を生成する。"""
    if not final_score_result.entries:
        params = _resolve_ranking_params(recommendation_request, config_versions)
        empty = _empty_ranked_items(params=params)
        metrics = FinalRankerRunMetrics(
            final_ranker_selected_count=0,
            final_ranker_latency_ms=0,
            final_ranker_mmr_applied=False,
            mmr_rank_shift_count=0,
            final_ranker_feature_match_missing_count=0,
            top_k_clipped=params.top_k_clipped,
        )
        return empty, metrics

    params = _resolve_ranking_params(recommendation_request, config_versions)
    if params.diversity_method != DEFAULT_DIVERSITY_METHOD:
        raise FinalRankerError(
            f"unsupported diversity_method: {params.diversity_method}",
        )
    if params.mmr_candidate_limit <= 0:
        raise FinalRankerError(
            f"mmr_candidate_limit must be positive: {params.mmr_candidate_limit}",
        )

    sorted_entries = sorted(
        final_score_result.entries,
        key=_final_score_sort_key,
    )
    pool = sorted_entries[: params.mmr_candidate_limit]
    feature_map = {entry.item_id: entry for entry in feature_match_result.entries}

    feature_match_missing_count = sum(
        1 for entry in pool if entry.item_id not in feature_map
    )

    use_mmr = (
        params.diversity_method == DEFAULT_DIVERSITY_METHOD
        and len(pool) > 1
        and params.top_k > 1
    )

    if use_mmr:
        selected, mmr_applied = _select_with_mmr(
            pool=pool,
            feature_map=feature_map,
            top_k=params.top_k,
            lambda_mmr=params.lambda_mmr,
        )
    else:
        selected = [
            _CandidateState(entry=entry)
            for entry in pool[: params.top_k]
        ]
        mmr_applied = False

    selected_at = datetime.now(UTC)
    ranked_entries = tuple(
        _build_ranked_entry(
            state=state,
            rank=index + 1,
            params=params,
            selected_at=selected_at,
            mmr_applied=mmr_applied,
        )
        for index, state in enumerate(selected)
    )

    mmr_rank_shift_count = 0
    if mmr_applied:
        mmr_rank_shift_count = _count_mmr_rank_shift(pool, selected, params.top_k)

    result = RankedItems(
        entries=ranked_entries,
        total_selected=len(ranked_entries),
        top_k_used=params.top_k,
        mmr_candidate_pool_size=len(pool),
        mmr_applied=mmr_applied,
        lambda_mmr_used=params.lambda_mmr if mmr_applied else None,
    )
    metrics = FinalRankerRunMetrics(
        final_ranker_selected_count=len(ranked_entries),
        final_ranker_latency_ms=0,
        final_ranker_mmr_applied=mmr_applied,
        mmr_rank_shift_count=mmr_rank_shift_count,
        final_ranker_feature_match_missing_count=feature_match_missing_count,
        top_k_clipped=params.top_k_clipped,
    )
    return result, metrics


def item_similarity(
    item_a_id: str,
    item_b_id: str,
    feature_map: dict[str, FeatureMatchEntry],
) -> float:
    """feature_match_result の 8 軸 match から商品間類似度を算出する（§8.3.2）。"""
    entry_a = feature_map.get(item_a_id)
    entry_b = feature_map.get(item_b_id)
    if entry_a is None or entry_b is None:
        return 0.0

    diffs: list[float] = []
    for feature_code in MVP_FEATURE_CODES:
        axis_a = entry_a.features.get(feature_code)
        axis_b = entry_b.features.get(feature_code)
        if axis_a is None or axis_b is None:
            continue
        diffs.append(abs(axis_a.match - axis_b.match))

    if not diffs:
        return 0.0

    average_distance = sum(diffs) / len(diffs)
    return min(1.0, max(0.0, 1.0 - average_distance))


def _select_with_mmr(
    *,
    pool: tuple[FinalScoreEntry, ...] | list[FinalScoreEntry],
    feature_map: dict[str, FeatureMatchEntry],
    top_k: int,
    lambda_mmr: float,
) -> tuple[list[_CandidateState], bool]:
    selected: list[_CandidateState] = []
    remaining = list(pool)

    while remaining and len(selected) < top_k:
        best_state: _CandidateState | None = None
        best_key: tuple[float, float, float, str] | None = None

        for candidate in remaining:
            max_similarity = 0.0
            if selected:
                max_similarity = max(
                    item_similarity(
                        candidate.item_id,
                        selected_item.entry.item_id,
                        feature_map,
                    )
                    for selected_item in selected
                )

            mmr_score = (
                lambda_mmr * candidate.pre_rank_score
                - (1.0 - lambda_mmr) * max_similarity
            )
            tiebreak = (
                -mmr_score,
                -candidate.pre_rank_score,
                -candidate.final_score,
                candidate.item_id,
            )
            if best_key is None or tiebreak < best_key:
                best_key = tiebreak
                best_state = _CandidateState(
                    entry=candidate,
                    mmr_score=round_to_scale(mmr_score, SCORE_DECIMAL_PLACES),
                    max_similarity_to_selected=round_to_scale(
                        max_similarity,
                        SCORE_DECIMAL_PLACES,
                    ),
                )

        if best_state is None:
            break

        selected.append(best_state)
        remaining = [entry for entry in remaining if entry.item_id != best_state.entry.item_id]

    return selected, True


def _build_ranked_entry(
    *,
    state: _CandidateState,
    rank: int,
    params: RankingParams,
    selected_at: datetime,
    mmr_applied: bool,
) -> RankedItemEntry:
    entry = state.entry
    diversity_penalty = 0.0
    if mmr_applied:
        diversity_penalty = round_to_scale(
            (1.0 - params.lambda_mmr) * state.max_similarity_to_selected,
            SCORE_DECIMAL_PLACES,
        )

    score_breakdown = _update_score_breakdown(
        entry.score_breakdown,
        diversity_penalty=diversity_penalty,
        max_similarity_to_selected=state.max_similarity_to_selected,
        mmr_score=state.mmr_score,
        diversity_method=params.diversity_method,
        lambda_mmr=params.lambda_mmr,
        include_mmr_score=mmr_applied,
    )

    return RankedItemEntry(
        item_id=entry.item_id,
        rank=rank,
        final_score=entry.final_score,
        pre_rank_score=entry.pre_rank_score,
        diversity_penalty=diversity_penalty,
        score_breakdown=score_breakdown,
        is_displayed=True,
        ranking_config_id=params.ranking_config_id,
        diversity_method=params.diversity_method,
        selected_at=selected_at,
        mmr_score=state.mmr_score if mmr_applied else None,
        max_similarity_to_selected=(
            state.max_similarity_to_selected if mmr_applied else None
        ),
    )


def _update_score_breakdown(
    base: dict[str, object],
    *,
    diversity_penalty: float,
    max_similarity_to_selected: float,
    mmr_score: float | None,
    diversity_method: str,
    lambda_mmr: float,
    include_mmr_score: bool,
) -> dict[str, object]:
    updated = copy.deepcopy(base)
    diversity_section: dict[str, object] = {
        "penalty": diversity_penalty,
        "max_similarity_to_selected": max_similarity_to_selected,
        "method": diversity_method,
        "lambda_mmr": lambda_mmr,
    }
    if include_mmr_score and mmr_score is not None:
        diversity_section["mmr_score"] = mmr_score
    updated["diversity"] = diversity_section
    return updated


def _resolve_ranking_params(
    recommendation_request: RecommendationRequest,
    config_versions: dict[str, str],
) -> RankingParams:
    raw_top_k = _raw_top_k(recommendation_request, config_versions)
    clipped_top_k, top_k_clipped = _clip_top_k(raw_top_k)

    raw_lambda = _resolve_config_float(
        config_versions,
        "lambda_mmr",
        default=DEFAULT_LAMBDA_MMR,
    )
    clipped_lambda, lambda_clipped = _clip_lambda_mmr(raw_lambda)

    mmr_candidate_limit = _resolve_config_int(
        config_versions,
        "mmr_candidate_limit",
        default=DEFAULT_MMR_CANDIDATE_LIMIT,
    )
    diversity_method = _resolve_config_str(
        config_versions,
        "diversity_method",
        default=DEFAULT_DIVERSITY_METHOD,
    )

    return RankingParams(
        top_k=clipped_top_k,
        top_k_clipped=top_k_clipped,
        lambda_mmr=clipped_lambda,
        lambda_mmr_clipped=lambda_clipped,
        mmr_candidate_limit=mmr_candidate_limit,
        diversity_method=diversity_method,
        ranking_config_id=config_versions.get("ranking_config_id", ""),
    )


def _raw_top_k(
    recommendation_request: RecommendationRequest,
    config_versions: dict[str, str],
) -> int:
    execution = recommendation_request.execution
    if execution is not None and execution.top_k is not None:
        return execution.top_k

    return _resolve_config_int(
        config_versions,
        "top_k_default",
        default=DEFAULT_TOP_K_DEFAULT,
    )


def _clip_top_k(raw_top_k: int) -> tuple[int, bool]:
    if raw_top_k < TOP_K_MIN:
        return TOP_K_MIN, True
    if raw_top_k > TOP_K_MAX:
        return TOP_K_MAX, True
    return raw_top_k, False


def _clip_lambda_mmr(raw_lambda: float) -> tuple[float, bool]:
    if raw_lambda < LAMBDA_MMR_MIN:
        return LAMBDA_MMR_MIN, True
    if raw_lambda > LAMBDA_MMR_MAX:
        return LAMBDA_MMR_MAX, True
    return raw_lambda, False


def _resolve_config_str(
    config_versions: dict[str, str],
    key: str,
    *,
    default: str,
) -> str:
    for candidate_key in (key, f"ranking_config.{key}"):
        value = config_versions.get(candidate_key)
        if value is not None and value.strip() != "":
            return value
    return default


def _resolve_config_int(
    config_versions: dict[str, str],
    key: str,
    *,
    default: int,
) -> int:
    raw = _resolve_config_str(config_versions, key, default=str(default))
    try:
        return int(raw)
    except ValueError as exc:
        raise FinalRankerError(f"invalid ranking config integer: {key}={raw}") from exc


def _resolve_config_float(
    config_versions: dict[str, str],
    key: str,
    *,
    default: float,
) -> float:
    raw = _resolve_config_str(config_versions, key, default=str(default))
    try:
        return float(raw)
    except ValueError as exc:
        raise FinalRankerError(f"invalid ranking config float: {key}={raw}") from exc


def _final_score_sort_key(entry: FinalScoreEntry) -> tuple[float, float, str]:
    return (-entry.pre_rank_score, -entry.final_score, entry.item_id)


def _count_mmr_rank_shift(
    pool: list[FinalScoreEntry] | tuple[FinalScoreEntry, ...],
    selected: list[_CandidateState],
    top_k: int,
) -> int:
    simple_order = sorted(pool, key=_final_score_sort_key)[:top_k]
    simple_ranks = {
        entry.item_id: index + 1 for index, entry in enumerate(simple_order)
    }
    shift_count = 0
    for index, state in enumerate(selected):
        mmr_rank = index + 1
        simple_rank = simple_ranks.get(state.entry.item_id)
        if simple_rank is not None and simple_rank != mmr_rank:
            shift_count += 1
    return shift_count


def _empty_ranked_items(*, params: RankingParams) -> RankedItems:
    return RankedItems(
        entries=(),
        total_selected=0,
        top_k_used=params.top_k,
        mmr_candidate_pool_size=0,
        mmr_applied=False,
        lambda_mmr_used=None,
    )
