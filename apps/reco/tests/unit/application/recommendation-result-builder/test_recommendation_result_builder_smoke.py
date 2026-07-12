"""MOD-RECO-021 Recommendation Result Builder smoke tests (implementation Task)."""

from __future__ import annotations

import pytest

from conftest import (
    _context_score_entry,
    _meaning_match_entry,
    _ranked_item_entry,
    _sample_context,
    _sample_ranked_items,
    build_result_builder,
)
from reco.application.context_scorer.models import ContextScoreResult
from reco.application.final_ranker.models import RankedItems
from reco.application.recommendation_result_builder import (
    RecommendationResultBuilderError,
    SURFACE_ERROR_CODE,
)
from reco.application.recommendation_result_builder.in_memory_repository import (
    InMemoryRecommendationResultRepository,
)
from reco.domain.recommendation.result import ResultStatus


def test_execute_builds_recommendation_result_with_joined_scores() -> None:
    context = _sample_context()
    builder = build_result_builder()

    result_context = builder.execute(context)

    result = result_context.recommendation_result
    assert result is not None
    assert result.result_status == ResultStatus.COMPLETED
    assert result.item_count == 1
    assert result.items[0].item_id == "item-001"
    assert result.items[0].rank == 1
    assert result.items[0].final_score == pytest.approx(0.78)
    assert result.version_info is not None
    assert "recommendation_result_id" in result.version_info
    assert "MOD-RECO-021" in result_context.completed_modules


def test_execute_persists_header_to_repository() -> None:
    repository = InMemoryRecommendationResultRepository()
    context = _sample_context()
    builder = build_result_builder(repository=repository)

    builder.execute(context)

    assert len(repository.headers_by_run_id) == 1
    header = repository.headers_by_run_id[context.run_id or ""]
    assert header.result_status.value == "generated"
    assert header.result_item_count == 1
    assert header.trace_id == "trace-result-builder"


def test_execute_succeeds_with_empty_ranked_items() -> None:
    context = _sample_context(
        ranked_items=RankedItems(
            entries=(),
            total_selected=0,
            top_k_used=10,
            mmr_candidate_pool_size=0,
            mmr_applied=False,
        ),
    )
    builder = build_result_builder()

    result_context = builder.execute(context)

    result = result_context.recommendation_result
    assert result is not None
    assert result.result_status == ResultStatus.EMPTY
    assert result.item_count == 0


def test_execute_echoes_rank_and_final_score_from_ranked_items() -> None:
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
        meaning_match_result=None,
    )
    from reco.application.meaning_match_aggregator.models import MeaningMatchResult

    context.meaning_match_result = MeaningMatchResult(
        entries=(
            _meaning_match_entry("item-a"),
            _meaning_match_entry("item-b"),
        ),
        total_aggregated=2,
    )
    builder = build_result_builder()

    result_context = builder.execute(context)

    result = result_context.recommendation_result
    assert result is not None
    assert [(item.item_id, item.rank, item.final_score) for item in result.items] == [
        ("item-a", 1, 0.91),
        ("item-b", 2, 0.82),
    ]


def test_execute_does_not_mutate_ranked_items_or_score_results() -> None:
    context = _sample_context()
    original_ranked = context.ranked_items
    original_context_score = context.context_score_result
    builder = build_result_builder()

    builder.execute(context)

    assert context.ranked_items is original_ranked
    assert context.context_score_result is original_context_score


def test_execute_raises_when_ranked_items_missing() -> None:
    context = _sample_context()
    context.ranked_items = None
    builder = build_result_builder()

    with pytest.raises(RecommendationResultBuilderError) as exc_info:
        builder.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_when_context_score_join_fails() -> None:
    context = _sample_context(
        context_score_result=ContextScoreResult(
            entries=(),
            lambda_ctx_applied=0.5,
            total_scored=0,
        ),
    )
    builder = build_result_builder()

    with pytest.raises(RecommendationResultBuilderError) as exc_info:
        builder.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_when_header_insert_fails() -> None:
    repository = InMemoryRecommendationResultRepository(should_fail_on_insert=True)
    context = _sample_context()
    builder = build_result_builder(repository=repository)

    with pytest.raises(RecommendationResultBuilderError) as exc_info:
        builder.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_on_duplicate_header_insert() -> None:
    repository = InMemoryRecommendationResultRepository()
    context = _sample_context()
    builder = build_result_builder(repository=repository)

    builder.execute(context)

    with pytest.raises(RecommendationResultBuilderError):
        builder.execute(_sample_context())
