"""MOD-RECO-019 Final Score Calculator smoke tests (implementation Task)."""

from __future__ import annotations

import pytest

from conftest import (
    _context_score_entry,
    _popularity_score_entry,
    _risk_penalty_entry,
    _sample_context,
    _sample_context_score_result,
    _sample_popularity_score_result,
    _sample_risk_penalty_result,
    build_scorer,
)
from reco.application.context_scorer.models import ContextScoreResult
from reco.application.final_score_calculator import (
    FINAL_SCORE_FORMULA_LINEAR_WEIGHTED_V1,
    FinalScoreCalculatorError,
    SURFACE_ERROR_CODE,
)
from reco.application.popularity_scorer.models import PopularityScoreResult
from reco.application.risk_scorer.models import RiskPenaltyResult


def test_execute_calculates_final_score_from_ranking_definition_example() -> None:
    context = _sample_context()
    scorer = build_scorer()

    result_context = scorer.execute(context)

    entry = result_context.final_score_result.entries[0]  # type: ignore[attr-defined]
    assert entry.pre_rank_score == pytest.approx(0.722)
    assert entry.final_score == pytest.approx(0.722)
    assert entry.diversity_penalty == pytest.approx(0.0)
    assert entry.final_score_formula == FINAL_SCORE_FORMULA_LINEAR_WEIGHTED_V1
    assert entry.ranking_weights_used.w_context == pytest.approx(0.70)
    assert entry.score_breakdown["pre_rank_score"] == pytest.approx(0.722)
    assert result_context.final_score_calculator_candidate_count == 1  # type: ignore[attr-defined]
    assert "MOD-RECO-019" in result_context.completed_modules


def test_execute_with_empty_risk_penalty_entries_succeeds() -> None:
    context = _sample_context(
        risk_penalty_result=RiskPenaltyResult(entries=(), total_scored=0),
    )
    scorer = build_scorer()

    result_context = scorer.execute(context)

    result = result_context.final_score_result  # type: ignore[attr-defined]
    assert result.total_scored == 0
    assert result.entries == ()
    assert result_context.final_score_calculator_candidate_count == 0  # type: ignore[attr-defined]


def test_execute_preserves_candidate_order() -> None:
    context = _sample_context(
        risk_penalty_result=_sample_risk_penalty_result(
            entries=(
                _risk_penalty_entry(item_id="item-001"),
                _risk_penalty_entry(item_id="item-002"),
            ),
        ),
        context_score_result=_sample_context_score_result(
            entries=(
                _context_score_entry(item_id="item-001"),
                _context_score_entry(item_id="item-002"),
            ),
        ),
        popularity_score_result=_sample_popularity_score_result(
            entries=(
                _popularity_score_entry(item_id="item-001"),
                _popularity_score_entry(item_id="item-002"),
            ),
        ),
    )
    scorer = build_scorer()

    result_context = scorer.execute(context)

    item_ids = [
        entry.item_id
        for entry in result_context.final_score_result.entries  # type: ignore[attr-defined]
    ]
    assert item_ids == ["item-001", "item-002"]


def test_execute_excludes_candidate_with_missing_context_score() -> None:
    context = _sample_context(
        risk_penalty_result=_sample_risk_penalty_result(
            entries=(
                _risk_penalty_entry(item_id="item-001"),
                _risk_penalty_entry(item_id="item-002"),
            ),
        ),
        context_score_result=_sample_context_score_result(
            entries=(
                _context_score_entry(item_id="item-001", context_score=0.84),
                _context_score_entry(item_id="item-002", context_score=None),
            ),
        ),
        popularity_score_result=_sample_popularity_score_result(
            entries=(
                _popularity_score_entry(item_id="item-001"),
                _popularity_score_entry(item_id="item-002"),
            ),
        ),
    )
    scorer = build_scorer()

    result_context = scorer.execute(context)

    result = result_context.final_score_result  # type: ignore[attr-defined]
    assert [entry.item_id for entry in result.entries] == ["item-001"]
    assert result_context.final_score_excluded_candidate_count == 1  # type: ignore[attr-defined]


def test_execute_does_not_mutate_input_results() -> None:
    context = _sample_context()
    original_context = context.context_score_result
    original_popularity = context.popularity_score_result  # type: ignore[attr-defined]
    original_risk = context.risk_penalty_result  # type: ignore[attr-defined]
    scorer = build_scorer()

    scorer.execute(context)

    assert context.context_score_result is original_context
    assert context.popularity_score_result is original_popularity  # type: ignore[attr-defined]
    assert context.risk_penalty_result is original_risk  # type: ignore[attr-defined]


def test_execute_raises_when_risk_penalty_result_missing() -> None:
    context = _sample_context()
    del context.risk_penalty_result  # type: ignore[attr-defined]
    scorer = build_scorer()

    with pytest.raises(FinalScoreCalculatorError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_for_join_mismatch() -> None:
    context = _sample_context(
        context_score_result=ContextScoreResult(
            entries=(_context_score_entry(item_id="other-item"),),
            lambda_ctx_applied=0.4,
            total_scored=1,
        ),
    )
    scorer = build_scorer()

    with pytest.raises(FinalScoreCalculatorError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_for_unsupported_final_score_formula() -> None:
    config_versions = {
        "ranking_config_id": "rc-1",
        "final_score_formula": "unsupported_formula",
    }
    context = _sample_context(config_versions=config_versions)
    scorer = build_scorer()

    with pytest.raises(FinalScoreCalculatorError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
