"""MOD-RECO-016 Context Scorer unit tests (module spec §14 unit)."""

from __future__ import annotations

import math
from dataclasses import fields

import pytest

from conftest import (
    _meaning_match_entry,
    _sample_context,
    _sample_meaning_match_result,
    build_scorer,
    run_scoring_from_context,
)
from reco.application.context_scorer import (
    CONTEXT_SCORE_FORMULA_LAMBDA_CTX_WEIGHTED,
    ContextScorerError,
    SURFACE_ERROR_CODE,
    run_context_scoring,
)
from reco.application.context_scorer.models import ContextScoreEntry
from reco.application.meaning_match_aggregator.models import MeaningMatchResult
from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)


def _single_entry_context(
    *,
    social_match: float,
    symbolic_match: float,
    lambda_ctx: float,
) -> ExecutionContext:
    return _sample_context(
        lambda_ctx=lambda_ctx,
        meaning_match_result=_sample_meaning_match_result(
            entries=(
                _meaning_match_entry(
                    item_id="item-001",
                    social_match=social_match,
                    symbolic_match=symbolic_match,
                ),
            ),
        ),
    )


# §14 No.1 正常系（基本算出）
def test_run_context_scoring_matches_matching_definition_example() -> None:
    context = _single_entry_context(
        social_match=0.82,
        symbolic_match=0.70,
        lambda_ctx=0.40,
    )

    result, metrics, warning_code = run_context_scoring(
        meaning_match_result=context.meaning_match_result,  # type: ignore[attr-defined]
        config_versions=context.config_versions,
        context=context,
    )

    entry = result.entries[0]
    assert entry.context_score == pytest.approx(0.772)
    assert entry.context_score_formula == CONTEXT_SCORE_FORMULA_LAMBDA_CTX_WEIGHTED
    assert result.lambda_ctx_applied == pytest.approx(0.4)
    assert metrics.lambda_ctx_applied == pytest.approx(0.4)
    assert warning_code is None


# §14 No.2 正常系（Social 重視）
def test_run_context_scoring_uses_social_match_when_lambda_ctx_is_zero() -> None:
    context = _single_entry_context(
        social_match=0.65,
        symbolic_match=0.91,
        lambda_ctx=0.0,
    )

    result, _ = run_scoring_from_context(context)

    assert result.entries[0].context_score == pytest.approx(0.65)


# §14 No.3 正常系（Symbolic 重視）
def test_run_context_scoring_uses_symbolic_match_when_lambda_ctx_is_one() -> None:
    context = _single_entry_context(
        social_match=0.65,
        symbolic_match=0.91,
        lambda_ctx=1.0,
    )

    result, _ = run_scoring_from_context(context)

    assert result.entries[0].context_score == pytest.approx(0.91)


# §14 No.4 正常系（バランス）
def test_run_context_scoring_averages_matches_when_lambda_ctx_is_half() -> None:
    context = _single_entry_context(
        social_match=0.60,
        symbolic_match=0.80,
        lambda_ctx=0.5,
    )

    result, _ = run_scoring_from_context(context)

    assert result.entries[0].context_score == pytest.approx(0.70)


# §14 No.5 正常系（候補複数）
def test_run_context_scoring_preserves_candidate_input_order() -> None:
    context = _sample_context(
        meaning_match_result=_sample_meaning_match_result(
            entries=(
                _meaning_match_entry(
                    item_id="item-a",
                    social_match=0.9,
                    symbolic_match=0.8,
                ),
                _meaning_match_entry(
                    item_id="item-b",
                    social_match=0.7,
                    symbolic_match=0.6,
                ),
                _meaning_match_entry(
                    item_id="item-c",
                    social_match=0.5,
                    symbolic_match=0.4,
                ),
            ),
        ),
    )

    result, metrics, _ = run_context_scoring(
        meaning_match_result=context.meaning_match_result,  # type: ignore[attr-defined]
        config_versions=context.config_versions,
        context=context,
    )

    assert [entry.item_id for entry in result.entries] == ["item-a", "item-b", "item-c"]
    assert result.total_scored == 3
    assert metrics.context_scorer_candidate_count == 3


# §14 No.6 lambda_ctx 参照
def test_run_context_scoring_clips_lambda_ctx_before_applying_to_all_candidates() -> None:
    context = _sample_context(
        lambda_ctx=1.25,
        meaning_match_result=_sample_meaning_match_result(
            entries=(
                _meaning_match_entry(
                    item_id="item-001",
                    social_match=0.2,
                    symbolic_match=0.9,
                ),
                _meaning_match_entry(
                    item_id="item-002",
                    social_match=0.4,
                    symbolic_match=0.6,
                ),
            ),
        ),
    )

    result, metrics = run_scoring_from_context(context)

    assert result.lambda_ctx_applied == pytest.approx(1.0)
    assert metrics.lambda_ctx_applied == pytest.approx(1.0)
    assert result.entries[0].context_score == pytest.approx(0.9)
    assert result.entries[1].context_score == pytest.approx(0.6)


# §14 No.7 境界値（完全一致）
def test_run_context_scoring_returns_one_when_all_matches_are_one() -> None:
    context = _single_entry_context(
        social_match=1.0,
        symbolic_match=1.0,
        lambda_ctx=0.4,
    )

    result, _ = run_scoring_from_context(context)

    assert result.entries[0].context_score == pytest.approx(1.0)


# §14 No.8 境界値（最大不一致）
def test_run_context_scoring_returns_zero_when_all_matches_are_zero() -> None:
    context = _single_entry_context(
        social_match=0.0,
        symbolic_match=0.0,
        lambda_ctx=0.4,
    )

    result, _ = run_scoring_from_context(context)

    assert result.entries[0].context_score == pytest.approx(0.0)


# §14 No.9 meaning_match_result 欠損
def test_run_context_scoring_raises_grs_rec_011_when_meaning_match_result_missing() -> None:
    context = _sample_context()
    del context.meaning_match_result  # type: ignore[attr-defined]

    with pytest.raises(ContextScorerError) as exc_info:
        run_scoring_from_context(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.10 match 欠損
@pytest.mark.parametrize("missing_field", ["social_match", "symbolic_match"])
def test_run_context_scoring_raises_grs_rec_011_when_match_field_missing(
    missing_field: str,
) -> None:
    entry = _meaning_match_entry(
        item_id="item-missing-match",
        social_match=0.5,
        symbolic_match=0.5,
    )
    object.__setattr__(entry, missing_field, None)
    context = _sample_context(
        meaning_match_result=_sample_meaning_match_result(entries=(entry,)),
    )

    with pytest.raises(ContextScorerError) as exc_info:
        run_scoring_from_context(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.11 入力 0 件
def test_run_context_scoring_succeeds_with_empty_entries_without_grs_rec_011() -> None:
    context = _sample_context(
        meaning_match_result=MeaningMatchResult(entries=(), total_aggregated=0),
    )

    result, metrics = run_scoring_from_context(context)

    assert result.total_scored == 0
    assert result.entries == ()
    assert metrics.context_scorer_candidate_count == 0


# §14 No.12 値域外 match / lambda_ctx
def test_run_context_scoring_clips_out_of_range_values_and_records_metric() -> None:
    context = _sample_context(
        lambda_ctx=-0.2,
        meaning_match_result=_sample_meaning_match_result(
            entries=(
                _meaning_match_entry(
                    item_id="item-clipped",
                    social_match=1.5,
                    symbolic_match=-0.3,
                ),
            ),
        ),
    )

    result, metrics = run_scoring_from_context(context)

    assert result.lambda_ctx_applied == pytest.approx(0.0)
    assert result.entries[0].context_score == pytest.approx(1.0)
    assert metrics.context_score_value_out_of_range_count == 3


# §14 No.13 lambda_ctx 両方欠落
def test_execute_uses_fallback_lambda_ctx_when_user_meaning_and_user_context_missing() -> None:
    context = _sample_context(
        meaning_match_result=_sample_meaning_match_result(
            entries=(
                _meaning_match_entry(
                    item_id="item-fallback",
                    social_match=0.4,
                    symbolic_match=0.8,
                ),
            ),
        ),
    )
    context.user_meaning = None  # type: ignore[assignment]
    context.user_context = None  # type: ignore[assignment]

    result_context = build_scorer().execute(context)

    assert result_context.lambda_ctx_applied == pytest.approx(0.5)  # type: ignore[attr-defined]
    entry = result_context.context_score_result.entries[0]  # type: ignore[attr-defined]
    assert entry.context_score == pytest.approx(0.6)
    warning_events = [
        event
        for event in result_context.error_log_events
        if event.get("level") == "warning"
    ]
    assert len(warning_events) == 1
    assert "lambda_ctx_both_missing" in warning_events[0]["message"]


# §14 No.14 lambda_ctx NaN / ±Inf
@pytest.mark.parametrize("non_finite_value", [math.nan, math.inf, -math.inf])
def test_run_context_scoring_raises_grs_rec_011_when_lambda_ctx_is_non_finite(
    non_finite_value: float,
) -> None:
    context = _sample_context(lambda_ctx=non_finite_value)

    with pytest.raises(ContextScorerError) as exc_info:
        run_scoring_from_context(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.15 未対応 formula
def test_run_context_scoring_raises_grs_rec_011_for_unsupported_formula() -> None:
    config_versions = {
        "matching_config_id": "cfg-1",
        "context_score_formula": "unsupported_formula",
    }
    context = _sample_context(config_versions=config_versions)

    with pytest.raises(ContextScorerError) as exc_info:
        run_scoring_from_context(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.17 責務境界
def test_run_context_scoring_uses_meaning_match_values_without_reaggregation() -> None:
    context = _sample_context(
        lambda_ctx=0.0,
        meaning_match_result=_sample_meaning_match_result(
            entries=(
                _meaning_match_entry(
                    item_id="item-boundary",
                    social_match=0.33,
                    symbolic_match=0.99,
                ),
            ),
        ),
    )

    result, _ = run_scoring_from_context(context)

    entry = result.entries[0]
    assert entry.context_score == pytest.approx(0.33)
    entry_field_names = {field.name for field in fields(ContextScoreEntry)}
    assert "ranking_penalty" not in entry_field_names
    assert "social_match" not in entry_field_names
    assert "symbolic_match" not in entry_field_names


# §14 No.20 meaning_match_result 不変
def test_run_context_scoring_does_not_mutate_meaning_match_result() -> None:
    context = _sample_context()
    original = context.meaning_match_result  # type: ignore[attr-defined]
    original_entries = original.entries

    run_scoring_from_context(context)

    assert context.meaning_match_result is original  # type: ignore[attr-defined]
    assert context.meaning_match_result.entries == original_entries  # type: ignore[attr-defined]
