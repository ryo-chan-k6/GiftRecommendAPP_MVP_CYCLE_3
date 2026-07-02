"""MOD-RECO-016 Context Scorer smoke tests (implementation Task)."""

from __future__ import annotations

import math

import pytest

from conftest import (
    _meaning_match_entry,
    _sample_context,
    _sample_meaning_match_result,
    build_scorer,
)
from reco.application.context_scorer import (
    CONTEXT_SCORE_FORMULA_LAMBDA_CTX_WEIGHTED,
    ContextScorerError,
    SURFACE_ERROR_CODE,
)
from reco.application.meaning_match_aggregator.models import MeaningMatchResult


def test_execute_calculates_context_score_from_matching_definition_example() -> None:
    context = _sample_context(lambda_ctx=0.40)
    scorer = build_scorer()

    result_context = scorer.execute(context)

    entry = result_context.context_score_result.entries[0]  # type: ignore[attr-defined]
    assert entry.context_score == pytest.approx(0.772)
    assert entry.context_score_formula == CONTEXT_SCORE_FORMULA_LAMBDA_CTX_WEIGHTED
    assert result_context.lambda_ctx_applied == pytest.approx(0.4)  # type: ignore[attr-defined]
    assert "MOD-RECO-016" in result_context.completed_modules


def test_execute_with_empty_meaning_match_entries_succeeds() -> None:
    context = _sample_context(
        meaning_match_result=MeaningMatchResult(entries=(), total_aggregated=0),
    )
    scorer = build_scorer()

    result_context = scorer.execute(context)

    result = result_context.context_score_result  # type: ignore[attr-defined]
    assert result.total_scored == 0
    assert result.entries == ()
    assert result_context.context_scorer_candidate_count == 0  # type: ignore[attr-defined]


def test_execute_preserves_candidate_order() -> None:
    context = _sample_context(
        meaning_match_result=_sample_meaning_match_result(
            entries=(
                _meaning_match_entry(
                    item_id="item-001",
                    social_match=0.9,
                    symbolic_match=0.8,
                ),
                _meaning_match_entry(
                    item_id="item-002",
                    social_match=0.7,
                    symbolic_match=0.6,
                ),
            ),
        ),
    )
    scorer = build_scorer()

    result_context = scorer.execute(context)

    item_ids = [
        entry.item_id
        for entry in result_context.context_score_result.entries  # type: ignore[attr-defined]
    ]
    assert item_ids == ["item-001", "item-002"]


def test_execute_does_not_mutate_meaning_match_result() -> None:
    context = _sample_context()
    original = context.meaning_match_result  # type: ignore[attr-defined]
    original_entry_count = len(original.entries)
    scorer = build_scorer()

    scorer.execute(context)

    assert context.meaning_match_result is original  # type: ignore[attr-defined]
    assert len(context.meaning_match_result.entries) == original_entry_count  # type: ignore[attr-defined]


def test_execute_raises_when_meaning_match_result_missing() -> None:
    context = _sample_context()
    del context.meaning_match_result  # type: ignore[attr-defined]
    scorer = build_scorer()

    with pytest.raises(ContextScorerError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_when_lambda_ctx_is_nan() -> None:
    context = _sample_context(lambda_ctx=math.nan)
    scorer = build_scorer()

    with pytest.raises(ContextScorerError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_for_unsupported_context_score_formula() -> None:
    config_versions = {
        "matching_config_id": "cfg-1",
        "context_score_formula": "unsupported_formula",
    }
    context = _sample_context(config_versions=config_versions)
    scorer = build_scorer()

    with pytest.raises(ContextScorerError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
