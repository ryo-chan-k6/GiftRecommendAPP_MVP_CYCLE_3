"""MOD-RECO-017 Popularity Scorer smoke tests (implementation Task)."""

from __future__ import annotations

import pytest

from conftest import (
    _context_score_entry,
    _sample_context,
    _sample_context_score_result,
    build_review_repository,
    build_scorer,
)
from reco.application.context_scorer.models import ContextScoreResult
from reco.application.popularity_scorer import (
    POPULARITY_FORMULA_RATING_REVIEW_COUNT_WEIGHTED,
    PopularityScorerError,
    SURFACE_ERROR_CODE,
)
from reco.application.popularity_scorer.models import ItemReviewSummary


def test_execute_calculates_popularity_score_from_ranking_definition_example() -> None:
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
    scorer = build_scorer(repository=repository)

    result_context = scorer.execute(context)

    entry = result_context.popularity_score_result.entries[0]  # type: ignore[attr-defined]
    assert entry.popularity_score == pytest.approx(0.788579, rel=1e-5)
    assert entry.popularity_formula == POPULARITY_FORMULA_RATING_REVIEW_COUNT_WEIGHTED
    assert result_context.popularity_scorer_candidate_count == 2  # type: ignore[attr-defined]
    assert result_context.popularity_score_result.max_review_count_in_candidates == 500  # type: ignore[attr-defined]
    assert "MOD-RECO-017" in result_context.completed_modules


def test_execute_with_empty_context_score_entries_succeeds() -> None:
    context = _sample_context(
        context_score_result=ContextScoreResult(
            entries=(),
            lambda_ctx_applied=0.4,
            total_scored=0,
        ),
    )
    scorer = build_scorer()

    result_context = scorer.execute(context)

    result = result_context.popularity_score_result  # type: ignore[attr-defined]
    assert result.total_scored == 0
    assert result.entries == ()
    assert result_context.popularity_scorer_candidate_count == 0  # type: ignore[attr-defined]


def test_execute_preserves_candidate_order() -> None:
    context = _sample_context(
        context_score_result=_sample_context_score_result(
            entries=(
                _context_score_entry(item_id="item-001"),
                _context_score_entry(item_id="item-002"),
            ),
        ),
    )
    scorer = build_scorer()

    result_context = scorer.execute(context)

    item_ids = [
        entry.item_id
        for entry in result_context.popularity_score_result.entries  # type: ignore[attr-defined]
    ]
    assert item_ids == ["item-001", "item-002"]


def test_execute_marks_signal_missing_when_review_row_absent() -> None:
    context = _sample_context(
        context_score_result=_sample_context_score_result(
            entries=(_context_score_entry(item_id="item-missing"),),
        ),
    )
    repository = build_review_repository(records={})
    scorer = build_scorer(repository=repository)

    result_context = scorer.execute(context)

    entry = result_context.popularity_score_result.entries[0]  # type: ignore[attr-defined]
    assert entry.signal_missing is True
    assert entry.popularity_score == pytest.approx(0.5)
    assert result_context.popularity_missing_signal_count == 1  # type: ignore[attr-defined]


def test_execute_does_not_mutate_context_score_result() -> None:
    context = _sample_context()
    original = context.context_score_result  # type: ignore[attr-defined]
    original_entry_count = len(original.entries)
    scorer = build_scorer()

    scorer.execute(context)

    assert context.context_score_result is original  # type: ignore[attr-defined]
    assert len(context.context_score_result.entries) == original_entry_count  # type: ignore[attr-defined]


def test_execute_raises_when_context_score_result_missing() -> None:
    context = _sample_context()
    del context.context_score_result  # type: ignore[attr-defined]
    scorer = build_scorer()

    with pytest.raises(PopularityScorerError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_for_unsupported_popularity_formula() -> None:
    config_versions = {
        "ranking_config_id": "rc-1",
        "popularity_formula": "unsupported_formula",
    }
    context = _sample_context(config_versions=config_versions)
    scorer = build_scorer()

    with pytest.raises(PopularityScorerError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_when_review_repository_fails() -> None:
    context = _sample_context()
    repository = build_review_repository(should_fail_on_fetch=True)
    scorer = build_scorer(repository=repository)

    with pytest.raises(PopularityScorerError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
