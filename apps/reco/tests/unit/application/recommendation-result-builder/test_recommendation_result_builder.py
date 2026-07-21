"""MOD-RECO-021 Recommendation Result Builder unit tests (module spec §14 unit)."""

from __future__ import annotations

import pytest

from conftest import (
    DEFAULT_MATCHING_CONFIG_ID,
    DEFAULT_RUN_ID,
    _context_score_entry,
    _meaning_match_entry,
    _ranked_item_entry,
    _sample_context,
    _sample_ranked_items,
    run_build_from_context,
)
from reco.application.config_version_resolver import DEFAULT_RANKING_CONFIG_ID
from reco.application.context_scorer.models import ContextScoreResult
from reco.application.final_ranker.models import RankedItems
from reco.application.meaning_match_aggregator.models import MeaningMatchResult
from reco.application.recommendation_result_builder import (
    RecommendationResultBuilderError,
    SURFACE_ERROR_CODE,
    resolve_version_ids,
)
from reco.application.recommendation_result_builder.models import ResultHeaderStatus


# §14 No.1 正常系（明細あり）
def test_build_recommendation_result_produces_header_and_item_domains() -> None:
    context = _sample_context()

    built, metrics = run_build_from_context(context)

    assert built.header.result_status == ResultHeaderStatus.GENERATED
    assert built.header.recommendation_run_id == DEFAULT_RUN_ID
    assert len(built.items) == 1
    assert built.items[0].item_id == "item-001"
    assert metrics.result_builder_item_count == 1
    assert metrics.zero_result_header_count == 0


# §14 No.2 正常系（rank / score エコー）
def test_build_recommendation_result_echoes_rank_and_final_score_from_ranked_items() -> None:
    entries = (
        _ranked_item_entry(item_id="item-a", rank=1, final_score=0.91),
        _ranked_item_entry(item_id="item-b", rank=2, final_score=0.82),
    )
    context = _sample_context(
        ranked_items=_sample_ranked_items(entries=entries),
        context_score_result=ContextScoreResult(
            entries=(
                _context_score_entry("item-a"),
                _context_score_entry("item-b"),
            ),
            lambda_ctx_applied=0.5,
            total_scored=2,
        ),
        meaning_match_result=MeaningMatchResult(
            entries=(
                _meaning_match_entry("item-a"),
                _meaning_match_entry("item-b"),
            ),
            total_aggregated=2,
        ),
    )

    built, _metrics = run_build_from_context(context)

    assert [(item.item_id, item.rank, item.final_score) for item in built.items] == [
        ("item-a", 1, 0.91),
        ("item-b", 2, 0.82),
    ]


# §14 No.3 context_score JOIN
def test_build_recommendation_result_joins_context_score_from_context_score_result() -> None:
    context = _sample_context(
        context_score_result=ContextScoreResult(
            entries=(_context_score_entry("item-001"),),
            lambda_ctx_applied=0.5,
            total_scored=1,
        ),
    )

    built, _metrics = run_build_from_context(context)

    assert built.items[0].context_score == pytest.approx(0.82)


# §14 No.4 score_breakdown 統合
def test_build_recommendation_result_merges_diversity_breakdown_with_joined_scores() -> None:
    context = _sample_context()

    built, metrics = run_build_from_context(context)
    breakdown = built.items[0].score_breakdown_json
    assert breakdown is not None
    assert breakdown["diversity"]["method"] == "mmr"
    assert breakdown["context_score"]["value"] == pytest.approx(0.82)
    assert breakdown["context_score"]["social_match"] == pytest.approx(0.86)
    assert breakdown["context_score"]["symbolic_match"] == pytest.approx(0.76)
    assert breakdown["popularity_score"]["value"] == pytest.approx(0.64)
    assert breakdown["risk_penalty"]["value"] == pytest.approx(0.08)
    assert breakdown["final_score"]["value"] == pytest.approx(0.78)
    assert metrics.score_breakdown_partial_count == 0


def test_build_recommendation_result_marks_partial_breakdown_when_popularity_and_risk_missing() -> (
    None
):
    from reco.application.popularity_scorer.models import PopularityScoreResult
    from reco.application.risk_scorer.models import RiskPenaltyResult

    context = _sample_context(
        popularity_score_result=PopularityScoreResult(
            entries=(),
            max_review_count_in_candidates=0,
            total_scored=0,
        ),
        risk_penalty_result=RiskPenaltyResult(entries=(), total_scored=0),
    )

    built, metrics = run_build_from_context(context)
    breakdown = built.items[0].score_breakdown_json
    assert breakdown is not None
    assert "popularity_score" not in breakdown
    assert "risk_penalty" not in breakdown
    assert metrics.score_breakdown_partial_count == 1


# §14 No.5 version 引き継ぎ
def test_build_recommendation_result_copies_run_versions_request_mode_and_trace_id() -> None:
    config_versions = {
        "semantic_config_version_id": "sem-v2",
        "model_version_id": "embed-v2",
        "matching_config_id": "match-v2",
        "ranking_config_id": "rank-v2",
    }
    context = _sample_context(
        trace_id="trace-mod-reco-021-version",
        config_versions=config_versions,
        retrieval_candidate_count=42,
    )

    built, _metrics = run_build_from_context(context)
    header = built.header

    assert header.semantic_config_version_id == "sem-v2"
    assert header.model_version_id == "embed-v2"
    assert header.matching_config_id == "match-v2"
    assert header.ranking_config_id == "rank-v2"
    assert header.request_mode == "ui"
    assert header.trace_id == "trace-mod-reco-021-version"
    assert header.candidate_count == 42
    assert header.reason_template_version_id is None


def test_resolve_version_ids_supports_alternate_config_version_keys() -> None:
    resolved = resolve_version_ids(
        {
            "semantic_config_version": "sem-alt",
            "model_version": "model-alt",
            "matching_config": DEFAULT_MATCHING_CONFIG_ID,
            "ranking_config": DEFAULT_RANKING_CONFIG_ID,
        },
    )

    assert resolved == (
        "sem-alt",
        "model-alt",
        DEFAULT_MATCHING_CONFIG_ID,
        DEFAULT_RANKING_CONFIG_ID,
    )


# §14 No.6 境界値（1 件）
def test_build_recommendation_result_sets_generated_status_for_single_item() -> None:
    context = _sample_context(
        ranked_items=_sample_ranked_items(entries=(_ranked_item_entry(),)),
    )

    built, metrics = run_build_from_context(context)

    assert built.header.result_status == ResultHeaderStatus.GENERATED
    assert built.header.result_item_count == 1
    assert metrics.result_builder_item_count == 1


# §14 No.7 境界値（0 件）
def test_build_recommendation_result_succeeds_with_empty_status_for_zero_items() -> None:
    context = _sample_context(
        ranked_items=RankedItems(
            entries=(),
            total_selected=0,
            top_k_used=10,
            mmr_candidate_pool_size=0,
            mmr_applied=False,
        ),
    )

    built, metrics = run_build_from_context(context)

    assert built.header.result_status == ResultHeaderStatus.EMPTY
    assert built.header.result_item_count == 0
    assert built.items == ()
    assert metrics.zero_result_header_count == 1


# §14 No.8 入力 0 件（防御的）
def test_build_recommendation_result_returns_empty_header_without_score_join_requirements() -> (
    None
):
    context = _sample_context(
        ranked_items=RankedItems(
            entries=(),
            total_selected=0,
            top_k_used=10,
            mmr_candidate_pool_size=0,
            mmr_applied=False,
        ),
        context_score_result=None,
        meaning_match_result=None,
    )

    built, _metrics = run_build_from_context(context)

    assert built.header.result_status == ResultHeaderStatus.EMPTY
    assert built.items == ()


# §14 No.9 ranked_items 欠損
def test_build_recommendation_result_raises_grs_rec_012_when_ranked_items_missing() -> None:
    context = _sample_context()
    context.ranked_items = None

    with pytest.raises(RecommendationResultBuilderError) as exc_info:
        run_build_from_context(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.10 context_score JOIN 失敗
def test_build_recommendation_result_raises_grs_rec_012_when_context_score_join_fails() -> (
    None
):
    context = _sample_context(
        context_score_result=ContextScoreResult(
            entries=(),
            lambda_ctx_applied=0.5,
            total_scored=0,
        ),
    )

    with pytest.raises(RecommendationResultBuilderError) as exc_info:
        run_build_from_context(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "context_score missing" in exc_info.value.message


def test_build_recommendation_result_raises_grs_rec_012_when_meaning_match_join_fails() -> (
    None
):
    context = _sample_context(
        meaning_match_result=MeaningMatchResult(entries=(), total_aggregated=0),
    )

    with pytest.raises(RecommendationResultBuilderError) as exc_info:
        run_build_from_context(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "meaning_match missing" in exc_info.value.message


# §14 No.15 上流 result 不変
def test_build_recommendation_result_does_not_mutate_ranked_items_or_score_results() -> None:
    context = _sample_context()
    original_ranked = context.ranked_items
    original_context_score = context.context_score_result
    original_ranked_breakdown = context.ranked_items.entries[0].score_breakdown  # type: ignore[union-attr]

    run_build_from_context(context)

    assert context.ranked_items is original_ranked
    assert context.context_score_result is original_context_score
    assert context.ranked_items.entries[0].score_breakdown == original_ranked_breakdown  # type: ignore[union-attr]


# §14 No.18 022 引き渡し
def test_build_recommendation_result_assigns_recommendation_result_item_id_for_each_item() -> None:
    context = _sample_context()

    built, _metrics = run_build_from_context(context)

    assert len(built.items) == 1
    item = built.items[0]
    assert item.recommendation_result_item_id
    assert item.recommendation_result_id == built.header.recommendation_result_id
