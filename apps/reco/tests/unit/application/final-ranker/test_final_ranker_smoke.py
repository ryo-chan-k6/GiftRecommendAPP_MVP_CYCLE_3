"""MOD-RECO-020 Final Ranker smoke tests (implementation Task)."""

from __future__ import annotations

import pytest

from conftest import (
    _feature_match_entry,
    _final_score_entry,
    _sample_context,
    _sample_feature_match_result,
    _sample_final_score_result,
    build_ranker,
)
from reco.application.final_ranker import FinalRankerError, SURFACE_ERROR_CODE
from reco.application.final_score_calculator.models import FinalScoreResult


def test_execute_assigns_rank_one_for_single_candidate() -> None:
    context = _sample_context()
    ranker = build_ranker()

    result_context = ranker.execute(context)

    ranked_items = result_context.ranked_items
    assert ranked_items is not None
    assert ranked_items.total_selected == 1
    assert ranked_items.entries[0].rank == 1
    assert ranked_items.entries[0].item_id == "item-001"
    assert ranked_items.mmr_applied is False
    assert result_context.final_ranker_selected_count == 1
    assert "MOD-RECO-020" in result_context.completed_modules


def test_execute_with_empty_final_score_entries_succeeds() -> None:
    context = _sample_context(
        final_score_result=FinalScoreResult(entries=(), total_scored=0),
    )
    ranker = build_ranker()

    result_context = ranker.execute(context)

    ranked_items = result_context.ranked_items
    assert ranked_items is not None
    assert ranked_items.total_selected == 0
    assert ranked_items.entries == ()
    assert result_context.final_ranker_selected_count == 0


def test_execute_limits_output_to_top_k() -> None:
    entries = tuple(
        _final_score_entry(item_id=f"item-{index:03d}", pre_rank_score=1.0 - index * 0.1)
        for index in range(5)
    )
    feature_entries = tuple(
        _feature_match_entry(item_id=f"item-{index:03d}") for index in range(5)
    )
    context = _sample_context(
        final_score_result=_sample_final_score_result(entries=entries),
        feature_match_result=_sample_feature_match_result(entries=feature_entries),
        top_k=3,
    )
    ranker = build_ranker()

    result_context = ranker.execute(context)

    ranked_items = result_context.ranked_items
    assert ranked_items is not None
    assert ranked_items.total_selected == 3
    assert ranked_items.top_k_used == 3
    assert [entry.rank for entry in ranked_items.entries] == [1, 2, 3]
    assert [entry.item_id for entry in ranked_items.entries] == [
        "item-000",
        "item-001",
        "item-002",
    ]


def test_execute_applies_mmr_and_updates_diversity_breakdown() -> None:
    entries = (
        _final_score_entry(item_id="item-a", pre_rank_score=0.90),
        _final_score_entry(item_id="item-b", pre_rank_score=0.85),
        _final_score_entry(item_id="item-c", pre_rank_score=0.84),
    )
    feature_entries = (
        _feature_match_entry(item_id="item-a", match_value=1.0),
        _feature_match_entry(item_id="item-b", match_value=1.0),
        _feature_match_entry(item_id="item-c", match_value=0.0),
    )
    context = _sample_context(
        final_score_result=_sample_final_score_result(entries=entries),
        feature_match_result=_sample_feature_match_result(entries=feature_entries),
        top_k=2,
    )
    ranker = build_ranker()

    result_context = ranker.execute(context)

    ranked_items = result_context.ranked_items
    assert ranked_items is not None
    assert ranked_items.mmr_applied is True
    assert ranked_items.entries[0].item_id == "item-a"
    assert ranked_items.entries[1].item_id == "item-c"
    diversity = ranked_items.entries[1].score_breakdown["diversity"]
    assert isinstance(diversity, dict)
    assert diversity["method"] == "mmr"
    assert diversity["lambda_mmr"] == pytest.approx(0.75)
    assert result_context.final_ranker_mmr_applied is True


def test_execute_clips_top_k_and_continues() -> None:
    context = _sample_context(top_k=0)
    ranker = build_ranker()

    result_context = ranker.execute(context)

    ranked_items = result_context.ranked_items
    assert ranked_items is not None
    assert ranked_items.top_k_used == 1
    assert result_context.top_k_clipped is True


def test_execute_does_not_mutate_input_results() -> None:
    context = _sample_context()
    original_final_score = context.final_score_result  # type: ignore[attr-defined]
    original_feature_match = context.feature_match_result
    ranker = build_ranker()

    ranker.execute(context)

    assert context.final_score_result is original_final_score  # type: ignore[attr-defined]
    assert context.feature_match_result is original_feature_match


def test_execute_raises_when_final_score_result_missing() -> None:
    context = _sample_context()
    del context.final_score_result  # type: ignore[attr-defined]
    ranker = build_ranker()

    with pytest.raises(FinalRankerError) as exc_info:
        ranker.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_when_feature_match_result_missing() -> None:
    context = _sample_context()
    context.feature_match_result = None
    ranker = build_ranker()

    with pytest.raises(FinalRankerError) as exc_info:
        ranker.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_for_unsupported_diversity_method() -> None:
    config_versions = {
        "ranking_config_id": "rc-1",
        "diversity_method": "cluster",
    }
    context = _sample_context(config_versions=config_versions)
    ranker = build_ranker()

    with pytest.raises(FinalRankerError) as exc_info:
        ranker.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
