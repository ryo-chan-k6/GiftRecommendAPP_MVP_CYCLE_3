"""MOD-RECO-017 Popularity Scorer unit tests (module spec §14 unit)."""

from __future__ import annotations

import math
from dataclasses import fields

import pytest

from conftest import (
    TrackingItemReviewSummaryRepository,
    _context_score_entry,
    _sample_context,
    _sample_context_score_result,
    build_review_repository,
    run_scoring_from_context,
)
from reco.application.context_scorer.models import ContextScoreResult
from reco.application.popularity_scorer import (
    POPULARITY_FORMULA_RATING_REVIEW_COUNT_WEIGHTED,
    PopularityScorerError,
    SURFACE_ERROR_CODE,
    run_popularity_scoring,
)
from reco.application.popularity_scorer.models import ItemReviewSummary, PopularityScoreEntry


def _single_entry_context(
    *,
    item_id: str = "item-001",
    review_average: float | None = 4.0,
    review_count: int | None = 120,
    extra_records: dict[str, ItemReviewSummary] | None = None,
) -> tuple:
    records = dict(extra_records or {})
    records[item_id] = ItemReviewSummary(
        review_average=review_average,
        review_count=review_count,
    )
    context = _sample_context(
        context_score_result=_sample_context_score_result(
            entries=(_context_score_entry(item_id=item_id),),
        ),
    )
    repository = build_review_repository(records=records)
    return context, repository


# §14 No.1 正常系（基本算出）
def test_run_popularity_scoring_matches_ranking_definition_example() -> None:
    context = _sample_context(
        context_score_result=_sample_context_score_result(
            entries=(
                _context_score_entry(item_id="item-001"),
                _context_score_entry(item_id="item-002"),
            ),
        ),
    )
    repository = build_review_repository(
        records={
            "item-001": ItemReviewSummary(review_average=4.0, review_count=120),
            "item-002": ItemReviewSummary(review_average=4.0, review_count=500),
        },
    )

    result, metrics = run_scoring_from_context(context, repository=repository)

    entry = result.entries[0]
    assert entry.popularity_score == pytest.approx(0.788579, rel=1e-5)
    assert entry.popularity_formula == POPULARITY_FORMULA_RATING_REVIEW_COUNT_WEIGHTED
    assert result.max_review_count_in_candidates == 500
    assert metrics.popularity_scorer_candidate_count == 2


# §14 No.2 正常系（高評価・多件数）
def test_run_popularity_scoring_returns_high_score_for_high_rating_and_review_count() -> None:
    context, repository = _single_entry_context(
        review_average=5.0,
        review_count=1000,
    )

    result, _ = run_scoring_from_context(context, repository=repository)

    entry = result.entries[0]
    assert entry.rating_score == pytest.approx(1.0)
    assert entry.review_count_score == pytest.approx(1.0)
    assert entry.popularity_score == pytest.approx(1.0)


# §14 No.3 正常系（低評価・少件数）
def test_run_popularity_scoring_returns_low_score_for_low_rating_and_zero_review_count() -> None:
    context = _sample_context(
        context_score_result=_sample_context_score_result(
            entries=(
                _context_score_entry(item_id="item-low"),
                _context_score_entry(item_id="item-max"),
            ),
        ),
    )
    repository = build_review_repository(
        records={
            "item-low": ItemReviewSummary(review_average=1.0, review_count=0),
            "item-max": ItemReviewSummary(review_average=4.0, review_count=100),
        },
    )

    result, _ = run_scoring_from_context(context, repository=repository)

    low_entry = result.entries[0]
    assert low_entry.rating_score == pytest.approx(0.2)
    assert low_entry.review_count_score == pytest.approx(0.0)
    assert low_entry.popularity_score == pytest.approx(0.12)


# §14 No.4 正常系（候補複数）
def test_run_popularity_scoring_preserves_candidate_input_order() -> None:
    context = _sample_context(
        context_score_result=_sample_context_score_result(
            entries=(
                _context_score_entry(item_id="item-a"),
                _context_score_entry(item_id="item-b"),
                _context_score_entry(item_id="item-c"),
            ),
        ),
    )
    repository = build_review_repository(
        records={
            "item-a": ItemReviewSummary(review_average=4.5, review_count=10),
            "item-b": ItemReviewSummary(review_average=3.5, review_count=20),
            "item-c": ItemReviewSummary(review_average=4.0, review_count=30),
        },
    )

    result, metrics = run_scoring_from_context(context, repository=repository)

    assert [entry.item_id for entry in result.entries] == ["item-a", "item-b", "item-c"]
    assert result.total_scored == 3
    assert metrics.popularity_scorer_candidate_count == 3


# §14 No.5 max_review_count
def test_run_popularity_scoring_normalizes_review_count_using_run_candidates_only() -> None:
    context = _sample_context(
        context_score_result=_sample_context_score_result(
            entries=(
                _context_score_entry(item_id="item-a"),
                _context_score_entry(item_id="item-b"),
            ),
        ),
    )
    repository = build_review_repository(
        records={
            "item-a": ItemReviewSummary(review_average=4.0, review_count=50),
            "item-b": ItemReviewSummary(review_average=4.0, review_count=200),
            "item-outside-run": ItemReviewSummary(review_average=5.0, review_count=10_000),
        },
    )

    result, _ = run_scoring_from_context(context, repository=repository)

    assert result.max_review_count_in_candidates == 200
    item_a = result.entries[0]
    expected_review_count_score = math.log1p(50) / math.log1p(200)
    assert item_a.review_count_score == pytest.approx(expected_review_count_score, rel=1e-5)


# §14 No.6 境界値（rating 満点）
def test_run_popularity_scoring_sets_rating_score_to_one_for_perfect_rating() -> None:
    context, repository = _single_entry_context(review_average=5.0, review_count=10)

    result, _ = run_scoring_from_context(context, repository=repository)

    assert result.entries[0].rating_score == pytest.approx(1.0)
    assert result.entries[0].review_average_used == pytest.approx(5.0)


# §14 No.7 境界値（review_count=0）
def test_run_popularity_scoring_sets_review_count_score_to_zero_when_count_is_zero() -> None:
    context = _sample_context(
        context_score_result=_sample_context_score_result(
            entries=(
                _context_score_entry(item_id="item-zero"),
                _context_score_entry(item_id="item-max"),
            ),
        ),
    )
    repository = build_review_repository(
        records={
            "item-zero": ItemReviewSummary(review_average=4.0, review_count=0),
            "item-max": ItemReviewSummary(review_average=4.0, review_count=100),
        },
    )

    result, _ = run_scoring_from_context(context, repository=repository)

    assert result.entries[0].review_count_score == pytest.approx(0.0)


# §14 No.8 境界値（max_review_count=0）
def test_run_popularity_scoring_uses_neutral_review_count_score_when_max_is_zero() -> None:
    context = _sample_context(
        context_score_result=_sample_context_score_result(
            entries=(_context_score_entry(item_id="item-zero-max"),),
        ),
    )
    repository = build_review_repository(
        records={
            "item-zero-max": ItemReviewSummary(review_average=4.0, review_count=0),
        },
    )

    result, _ = run_scoring_from_context(context, repository=repository)

    assert result.max_review_count_in_candidates == 0
    assert result.entries[0].review_count_score == pytest.approx(0.5)


# §14 No.9 欠損（行不在）
def test_run_popularity_scoring_marks_signal_missing_and_uses_neutral_score_when_row_absent() -> None:
    context = _sample_context(
        context_score_result=_sample_context_score_result(
            entries=(_context_score_entry(item_id="item-missing"),),
        ),
    )
    repository = build_review_repository(records={})

    result, metrics = run_scoring_from_context(context, repository=repository)

    entry = result.entries[0]
    assert entry.signal_missing is True
    assert entry.popularity_score == pytest.approx(0.5)
    assert metrics.popularity_missing_signal_count == 1


# §14 No.10 欠損（rating NULL）
def test_run_popularity_scoring_continues_with_neutral_rating_when_review_average_is_null() -> None:
    context = _sample_context(
        context_score_result=_sample_context_score_result(
            entries=(_context_score_entry(item_id="item-null-rating"),),
        ),
    )
    repository = build_review_repository(
        records={
            "item-null-rating": ItemReviewSummary(review_average=None, review_count=10),
        },
    )

    result, metrics = run_scoring_from_context(context, repository=repository)

    entry = result.entries[0]
    assert entry.rating_score == pytest.approx(0.5)
    assert entry.review_average_used is None
    assert entry.signal_missing is True
    assert metrics.popularity_missing_signal_count == 1


# §14 No.11 入力 0 件
def test_run_popularity_scoring_succeeds_with_empty_entries_without_grs_rec_012() -> None:
    context = _sample_context(
        context_score_result=ContextScoreResult(
            entries=(),
            lambda_ctx_applied=0.4,
            total_scored=0,
        ),
    )

    result, metrics = run_scoring_from_context(context)

    assert result.total_scored == 0
    assert result.entries == ()
    assert metrics.popularity_scorer_candidate_count == 0


# §14 No.13 未対応 formula
def test_run_popularity_scoring_raises_grs_rec_012_for_unsupported_formula() -> None:
    context = _sample_context(
        config_versions={
            "ranking_config_id": "rc-1",
            "popularity_formula": "unsupported_formula",
        },
    )

    with pytest.raises(PopularityScorerError) as exc_info:
        run_scoring_from_context(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.16 責務境界
def test_run_popularity_scoring_does_not_emit_final_score_or_ranking_fields() -> None:
    context, repository = _single_entry_context()

    result, _ = run_scoring_from_context(context, repository=repository)

    entry_field_names = {field.name for field in fields(PopularityScoreEntry)}
    assert "final_score" not in entry_field_names
    assert "risk_penalty" not in entry_field_names
    assert "context_score" not in entry_field_names
    assert "rank" not in entry_field_names


# §14 No.19 context_score_result 不変
def test_run_popularity_scoring_does_not_mutate_context_score_result() -> None:
    context = _sample_context()
    original = context.context_score_result  # type: ignore[attr-defined]
    original_entries = original.entries

    run_scoring_from_context(context)

    assert context.context_score_result is original  # type: ignore[attr-defined]
    assert context.context_score_result.entries == original_entries  # type: ignore[attr-defined]


# §14 No.20 N+1 回避
def test_run_popularity_scoring_fetches_review_summaries_in_one_batch() -> None:
    context = _sample_context(
        context_score_result=_sample_context_score_result(
            entries=(
                _context_score_entry(item_id="item-001"),
                _context_score_entry(item_id="item-002"),
                _context_score_entry(item_id="item-003"),
            ),
        ),
    )
    repository = TrackingItemReviewSummaryRepository(
        records={
            "item-001": ItemReviewSummary(review_average=4.0, review_count=10),
            "item-002": ItemReviewSummary(review_average=4.0, review_count=20),
            "item-003": ItemReviewSummary(review_average=4.0, review_count=30),
        },
    )

    run_scoring_from_context(context, repository=repository)

    assert len(repository.fetch_calls) == 1
    assert repository.fetch_calls[0] == ("item-001", "item-002", "item-003")


def test_run_popularity_scoring_raises_when_total_scored_is_inconsistent() -> None:
    context = _sample_context(
        context_score_result=ContextScoreResult(
            entries=(_context_score_entry(item_id="item-001"),),
            lambda_ctx_applied=0.4,
            total_scored=99,
        ),
    )

    with pytest.raises(PopularityScorerError) as exc_info:
        run_popularity_scoring(
            context_score_result=context.context_score_result,  # type: ignore[attr-defined]
            config_versions=context.config_versions,
            review_summary_repository=build_review_repository(),
        )

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
