"""MOD-RECO-020 Final Ranker unit tests (module spec §14 unit)."""

from __future__ import annotations

import pytest

from conftest import (
    _feature_match_entry,
    _final_score_entry,
    _sample_context,
    _sample_feature_match_result,
    _sample_final_score_result,
    run_ranking_from_context,
)
from reco.application.final_ranker import (
    DEFAULT_LAMBDA_MMR,
    DEFAULT_TOP_K_DEFAULT,
    item_similarity,
    run_final_ranking,
)
from reco.application.final_ranker.constants import TOP_K_MAX
from reco.application.final_score_calculator.models import FinalScoreResult


def _ranking_inputs(
    *,
    final_entries: tuple | None = None,
    feature_entries: tuple | None = None,
    config_versions: dict[str, str] | None = None,
    top_k: int | None = None,
):
    context = _sample_context(
        final_score_result=_sample_final_score_result(entries=final_entries)
        if final_entries is not None
        else _sample_final_score_result(),
        feature_match_result=_sample_feature_match_result(entries=feature_entries)
        if feature_entries is not None
        else _sample_feature_match_result(),
        config_versions=config_versions,
        top_k=top_k,
    )
    return (
        context.final_score_result,  # type: ignore[attr-defined]
        context.feature_match_result,
        context.recommendation_request,
        context.config_versions,
    )


# §14 No.1 正常系（MMR 基本）
def test_run_final_ranking_matches_mmr_pseudo_code_selection_order_and_scores() -> None:
    final_entries = (
        _final_score_entry(item_id="item-a", pre_rank_score=0.90),
        _final_score_entry(item_id="item-b", pre_rank_score=0.85),
        _final_score_entry(item_id="item-c", pre_rank_score=0.84),
    )
    feature_entries = (
        _feature_match_entry(item_id="item-a", match_value=1.0),
        _feature_match_entry(item_id="item-b", match_value=1.0),
        _feature_match_entry(item_id="item-c", match_value=0.0),
    )
    final_score_result, feature_match_result, request, config_versions = _ranking_inputs(
        final_entries=final_entries,
        feature_entries=feature_entries,
        top_k=2,
    )

    result, metrics = run_final_ranking(
        final_score_result=final_score_result,
        feature_match_result=feature_match_result,
        recommendation_request=request,
        config_versions=config_versions,
    )

    assert [entry.item_id for entry in result.entries] == ["item-a", "item-c"]
    assert result.entries[0].mmr_score == pytest.approx(0.75 * 0.90)
    assert result.entries[1].mmr_score == pytest.approx(0.75 * 0.84)
    assert metrics.final_ranker_mmr_applied is True


# §14 No.2 正常系（rank 連番）
def test_run_final_ranking_assigns_consecutive_ranks() -> None:
    final_entries = tuple(
        _final_score_entry(item_id=f"item-{index:03d}", pre_rank_score=1.0 - index * 0.1)
        for index in range(4)
    )
    feature_entries = tuple(
        _feature_match_entry(item_id=f"item-{index:03d}") for index in range(4)
    )
    final_score_result, feature_match_result, request, config_versions = _ranking_inputs(
        final_entries=final_entries,
        feature_entries=feature_entries,
        top_k=4,
    )

    result, _ = run_final_ranking(
        final_score_result=final_score_result,
        feature_match_result=feature_match_result,
        recommendation_request=request,
        config_versions=config_versions,
    )

    assert [entry.rank for entry in result.entries] == [1, 2, 3, 4]


# §14 No.3 正常系（top_k）
def test_run_final_ranking_limits_output_to_top_k_when_candidates_exceed_top_k() -> None:
    final_entries = tuple(
        _final_score_entry(item_id=f"item-{index:03d}", pre_rank_score=1.0 - index * 0.05)
        for index in range(8)
    )
    feature_entries = tuple(
        _feature_match_entry(item_id=f"item-{index:03d}") for index in range(8)
    )
    final_score_result, feature_match_result, request, config_versions = _ranking_inputs(
        final_entries=final_entries,
        feature_entries=feature_entries,
        top_k=3,
    )

    result, _ = run_final_ranking(
        final_score_result=final_score_result,
        feature_match_result=feature_match_result,
        recommendation_request=request,
        config_versions=config_versions,
    )

    assert result.total_selected == 3
    assert result.top_k_used == 3


# §14 No.4 多様性効果
def test_run_final_ranking_prefers_diverse_candidate_over_similar_high_score() -> None:
    final_entries = (
        _final_score_entry(item_id="item-a", pre_rank_score=0.90),
        _final_score_entry(item_id="item-b", pre_rank_score=0.85),
        _final_score_entry(item_id="item-c", pre_rank_score=0.84),
    )
    feature_entries = (
        _feature_match_entry(item_id="item-a", match_value=1.0),
        _feature_match_entry(item_id="item-b", match_value=1.0),
        _feature_match_entry(item_id="item-c", match_value=0.0),
    )
    final_score_result, feature_match_result, request, config_versions = _ranking_inputs(
        final_entries=final_entries,
        feature_entries=feature_entries,
        top_k=2,
    )

    result, _ = run_final_ranking(
        final_score_result=final_score_result,
        feature_match_result=feature_match_result,
        recommendation_request=request,
        config_versions=config_versions,
    )

    assert result.entries[1].item_id == "item-c"
    assert result.entries[1].item_id != "item-b"


# §14 No.5 非 MMR フォールバック
def test_run_final_ranking_falls_back_to_pre_rank_order_when_top_k_is_one() -> None:
    final_entries = (
        _final_score_entry(item_id="item-a", pre_rank_score=0.90),
        _final_score_entry(item_id="item-b", pre_rank_score=0.85),
    )
    feature_entries = (
        _feature_match_entry(item_id="item-a", match_value=1.0),
        _feature_match_entry(item_id="item-b", match_value=0.0),
    )
    final_score_result, feature_match_result, request, config_versions = _ranking_inputs(
        final_entries=final_entries,
        feature_entries=feature_entries,
        top_k=1,
    )

    result, _ = run_final_ranking(
        final_score_result=final_score_result,
        feature_match_result=feature_match_result,
        recommendation_request=request,
        config_versions=config_versions,
    )

    assert result.mmr_applied is False
    assert result.entries[0].item_id == "item-a"
    assert result.entries[0].mmr_score is None


# §14 No.6 top_k 解決
def test_run_final_ranking_prefers_request_top_k_over_default() -> None:
    final_entries = tuple(
        _final_score_entry(item_id=f"item-{index:03d}", pre_rank_score=1.0 - index * 0.1)
        for index in range(5)
    )
    feature_entries = tuple(
        _feature_match_entry(item_id=f"item-{index:03d}") for index in range(5)
    )
    final_score_result, feature_match_result, request, config_versions = _ranking_inputs(
        final_entries=final_entries,
        feature_entries=feature_entries,
        top_k=3,
    )

    result, _ = run_final_ranking(
        final_score_result=final_score_result,
        feature_match_result=feature_match_result,
        recommendation_request=request,
        config_versions=config_versions,
    )

    assert result.top_k_used == 3


def test_run_final_ranking_uses_top_k_default_when_request_top_k_unspecified() -> None:
    context = _sample_context(top_k=None)
    final_score_result = context.final_score_result  # type: ignore[attr-defined]
    entries = tuple(
        _final_score_entry(item_id=f"item-{index:03d}", pre_rank_score=1.0 - index * 0.01)
        for index in range(DEFAULT_TOP_K_DEFAULT + 2)
    )
    final_score_result = FinalScoreResult(entries=entries, total_scored=len(entries))
    feature_entries = tuple(
        _feature_match_entry(item_id=entry.item_id) for entry in entries
    )

    result, _ = run_final_ranking(
        final_score_result=final_score_result,
        feature_match_result=_sample_feature_match_result(entries=feature_entries),
        recommendation_request=context.recommendation_request,
        config_versions=context.config_versions,
    )

    assert result.top_k_used == DEFAULT_TOP_K_DEFAULT
    assert result.total_selected == DEFAULT_TOP_K_DEFAULT


# §14 No.7 score_breakdown 更新
def test_run_final_ranking_updates_diversity_section_with_mmr_metadata() -> None:
    final_entries = (
        _final_score_entry(item_id="item-a", pre_rank_score=0.90),
        _final_score_entry(item_id="item-b", pre_rank_score=0.85),
    )
    feature_entries = (
        _feature_match_entry(item_id="item-a", match_value=1.0),
        _feature_match_entry(item_id="item-b", match_value=0.0),
    )
    final_score_result, feature_match_result, request, config_versions = _ranking_inputs(
        final_entries=final_entries,
        feature_entries=feature_entries,
        top_k=2,
    )

    result, _ = run_final_ranking(
        final_score_result=final_score_result,
        feature_match_result=feature_match_result,
        recommendation_request=request,
        config_versions=config_versions,
    )

    second_entry = result.entries[1]
    diversity = second_entry.score_breakdown["diversity"]
    assert isinstance(diversity, dict)
    assert diversity["method"] == "mmr"
    assert diversity["lambda_mmr"] == pytest.approx(DEFAULT_LAMBDA_MMR)
    assert "mmr_score" in diversity
    assert "max_similarity_to_selected" in diversity
    assert second_entry.max_similarity_to_selected is not None


# §14 No.8 境界値（候補 1 件）
def test_run_final_ranking_succeeds_for_single_candidate_without_mmr() -> None:
    final_score_result, feature_match_result, request, config_versions = _ranking_inputs()

    result, metrics = run_final_ranking(
        final_score_result=final_score_result,
        feature_match_result=feature_match_result,
        recommendation_request=request,
        config_versions=config_versions,
    )

    assert result.total_selected == 1
    assert result.entries[0].rank == 1
    assert result.mmr_applied is False
    assert metrics.final_ranker_mmr_applied is False


# §14 No.9 境界値（候補 < top_k）
def test_run_final_ranking_selects_all_candidates_when_pool_smaller_than_top_k() -> None:
    final_entries = (
        _final_score_entry(item_id="item-a", pre_rank_score=0.90),
        _final_score_entry(item_id="item-b", pre_rank_score=0.80),
    )
    feature_entries = (
        _feature_match_entry(item_id="item-a"),
        _feature_match_entry(item_id="item-b"),
    )
    final_score_result, feature_match_result, request, config_versions = _ranking_inputs(
        final_entries=final_entries,
        feature_entries=feature_entries,
        top_k=10,
    )

    result, _ = run_final_ranking(
        final_score_result=final_score_result,
        feature_match_result=feature_match_result,
        recommendation_request=request,
        config_versions=config_versions,
    )

    assert result.total_selected == 2
    assert result.top_k_used == 10


# §14 No.10 境界値（top_k clip）
def test_run_final_ranking_clips_top_k_below_minimum_and_continues() -> None:
    context = _sample_context(top_k=0)

    result, metrics = run_ranking_from_context(context)

    assert result.top_k_used == 1
    assert metrics.top_k_clipped is True


def test_run_final_ranking_clips_top_k_above_maximum_and_continues() -> None:
    entries = tuple(
        _final_score_entry(item_id=f"item-{index:03d}", pre_rank_score=1.0 - index * 0.001)
        for index in range(TOP_K_MAX + 5)
    )
    feature_entries = tuple(
        _feature_match_entry(item_id=f"item-{index:03d}") for index in range(TOP_K_MAX + 5)
    )
    final_score_result, feature_match_result, request, config_versions = _ranking_inputs(
        final_entries=entries,
        feature_entries=feature_entries,
        top_k=TOP_K_MAX + 10,
    )

    result, metrics = run_final_ranking(
        final_score_result=final_score_result,
        feature_match_result=feature_match_result,
        recommendation_request=request,
        config_versions=config_versions,
    )

    assert result.top_k_used == TOP_K_MAX
    assert result.total_selected == TOP_K_MAX
    assert metrics.top_k_clipped is True


# §14 No.11 入力 0 件
def test_run_final_ranking_succeeds_with_empty_final_score_entries() -> None:
    context = _sample_context(
        final_score_result=FinalScoreResult(entries=(), total_scored=0),
    )

    result, metrics = run_ranking_from_context(context)

    assert result.total_selected == 0
    assert result.entries == ()
    assert metrics.final_ranker_selected_count == 0


# §14 No.15 同点タイブレーク
def test_run_final_ranking_breaks_mmr_ties_by_item_id() -> None:
    final_entries = (
        _final_score_entry(item_id="item-z", pre_rank_score=0.85),
        _final_score_entry(item_id="item-a", pre_rank_score=0.85),
        _final_score_entry(item_id="item-m", pre_rank_score=0.90),
    )
    feature_entries = (
        _feature_match_entry(item_id="item-z", match_value=0.5),
        _feature_match_entry(item_id="item-a", match_value=0.5),
        _feature_match_entry(item_id="item-m", match_value=0.5),
    )
    final_score_result, feature_match_result, request, config_versions = _ranking_inputs(
        final_entries=final_entries,
        feature_entries=feature_entries,
        top_k=3,
    )

    result, _ = run_final_ranking(
        final_score_result=final_score_result,
        feature_match_result=feature_match_result,
        recommendation_request=request,
        config_versions=config_versions,
    )

    assert result.entries[0].item_id == "item-m"
    assert [entry.item_id for entry in result.entries[1:]] == ["item-a", "item-z"]


def test_item_similarity_returns_zero_when_feature_match_missing() -> None:
    feature_map = {
        "item-a": _feature_match_entry(item_id="item-a", match_value=0.8),
    }

    assert item_similarity("item-a", "item-missing", feature_map) == 0.0


def test_item_similarity_uses_eight_axis_match_profile() -> None:
    entry_a = _feature_match_entry(item_id="item-a", match_value=1.0)
    entry_b = _feature_match_entry(item_id="item-b", match_value=0.0)
    feature_map = {"item-a": entry_a, "item-b": entry_b}

    assert item_similarity("item-a", "item-b", feature_map) == pytest.approx(0.0)
