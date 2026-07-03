"""MOD-RECO-019 Final Score Calculator unit tests (module spec §14 unit)."""

from __future__ import annotations

from dataclasses import fields

import pytest

from conftest import (
    _context_score_entry,
    _popularity_score_entry,
    _risk_penalty_entry,
    _sample_context,
    _sample_context_score_result,
    _sample_popularity_score_result,
    _sample_risk_penalty_result,
    run_scoring_from_context,
)
from reco.application.context_scorer.models import ContextScoreResult
from reco.application.final_score_calculator import (
    DEFAULT_W_CONTEXT,
    DEFAULT_W_POPULARITY,
    DEFAULT_W_RISK,
    FINAL_SCORE_FORMULA_LINEAR_WEIGHTED_V1,
    FinalScoreCalculatorError,
    FinalScoreEntry,
    SURFACE_ERROR_CODE,
    run_final_score_calculation,
)
from reco.application.popularity_scorer.models import PopularityScoreResult
from reco.application.risk_scorer.models import RiskPenaltyResult


def _single_entry_context(
    *,
    context_score: float | None = 0.84,
    popularity_score: float | None = 0.72,
    risk_penalty: float | None = 0.10,
    config_versions: dict[str, str] | None = None,
) -> tuple:
    context = _sample_context(
        config_versions=config_versions,
        context_score_result=_sample_context_score_result(
            entries=(_context_score_entry(item_id="item-001", context_score=context_score),),
        ),
        popularity_score_result=_sample_popularity_score_result(
            entries=(
                _popularity_score_entry(item_id="item-001", popularity_score=popularity_score),
            ),
        ),
        risk_penalty_result=_sample_risk_penalty_result(
            entries=(_risk_penalty_entry(item_id="item-001", risk_penalty=risk_penalty),),
        ),
    )
    return context


# §14 No.1 正常系（基本算出）
def test_run_final_score_calculation_matches_ranking_definition_example() -> None:
    context = _single_entry_context()

    result, metrics = run_scoring_from_context(context)

    entry = result.entries[0]
    assert entry.pre_rank_score == pytest.approx(0.722)
    assert entry.final_score == pytest.approx(0.722)
    assert entry.diversity_penalty == pytest.approx(0.0)
    assert entry.final_score_formula == FINAL_SCORE_FORMULA_LINEAR_WEIGHTED_V1
    assert entry.ranking_weights_used.w_context == pytest.approx(DEFAULT_W_CONTEXT)
    assert metrics.final_score_calculator_candidate_count == 1


# §14 No.2 正常系（context 最重視）
def test_run_final_score_calculation_favors_high_context_score() -> None:
    high_context_context = _single_entry_context(
        context_score=1.0,
        popularity_score=0.1,
        risk_penalty=0.0,
    )
    low_context_context = _single_entry_context(
        context_score=0.1,
        popularity_score=1.0,
        risk_penalty=0.0,
    )

    high_context_result, _ = run_scoring_from_context(high_context_context)
    low_context_result, _ = run_scoring_from_context(low_context_context)

    assert high_context_result.entries[0].final_score > low_context_result.entries[0].final_score


# §14 No.3 正常系（risk 減点）
def test_run_final_score_calculation_reduces_score_for_high_risk_penalty() -> None:
    baseline_context = _single_entry_context(risk_penalty=0.0)
    high_risk_context = _single_entry_context(risk_penalty=1.0)

    baseline_result, _ = run_scoring_from_context(baseline_context)
    high_risk_result, _ = run_scoring_from_context(high_risk_context)

    assert high_risk_result.entries[0].final_score < baseline_result.entries[0].final_score
    assert high_risk_result.entries[0].pre_rank_score == pytest.approx(0.632)


# §14 No.4 正常系（候補複数）
def test_run_final_score_calculation_preserves_candidate_input_order() -> None:
    context = _sample_context(
        risk_penalty_result=_sample_risk_penalty_result(
            entries=(
                _risk_penalty_entry(item_id="item-a"),
                _risk_penalty_entry(item_id="item-b"),
                _risk_penalty_entry(item_id="item-c"),
            ),
        ),
        context_score_result=_sample_context_score_result(
            entries=(
                _context_score_entry(item_id="item-a"),
                _context_score_entry(item_id="item-b"),
                _context_score_entry(item_id="item-c"),
            ),
        ),
        popularity_score_result=_sample_popularity_score_result(
            entries=(
                _popularity_score_entry(item_id="item-a"),
                _popularity_score_entry(item_id="item-b"),
                _popularity_score_entry(item_id="item-c"),
            ),
        ),
    )

    result, metrics = run_scoring_from_context(context)

    assert [entry.item_id for entry in result.entries] == ["item-a", "item-b", "item-c"]
    assert result.total_scored == 3
    assert metrics.final_score_calculator_candidate_count == 3


# §14 No.5 score_breakdown
def test_run_final_score_calculation_builds_score_breakdown_matching_formula() -> None:
    context = _single_entry_context()

    result, _ = run_scoring_from_context(context)

    entry = result.entries[0]
    breakdown = entry.score_breakdown
    assert breakdown["context"]["score"] == pytest.approx(0.84)
    assert breakdown["context"]["weight"] == pytest.approx(DEFAULT_W_CONTEXT)
    assert breakdown["context"]["contribution"] == pytest.approx(0.588)
    assert breakdown["popularity"]["score"] == pytest.approx(0.72)
    assert breakdown["popularity"]["weight"] == pytest.approx(DEFAULT_W_POPULARITY)
    assert breakdown["popularity"]["contribution"] == pytest.approx(0.144)
    assert breakdown["risk"]["penalty"] == pytest.approx(0.10)
    assert breakdown["risk"]["weight"] == pytest.approx(DEFAULT_W_RISK)
    assert breakdown["risk"]["contribution"] == pytest.approx(-0.010)
    assert breakdown["diversity"]["penalty"] == pytest.approx(0.0)
    assert breakdown["pre_rank_score"] == pytest.approx(0.722)
    assert breakdown["final_score"] == pytest.approx(0.722)


# §14 No.6 境界値（満点）
def test_run_final_score_calculation_reaches_maximum_with_perfect_input_scores() -> None:
    context = _single_entry_context(
        context_score=1.0,
        popularity_score=1.0,
        risk_penalty=0.0,
    )

    result, _ = run_scoring_from_context(context)

    entry = result.entries[0]
    assert entry.pre_rank_score == pytest.approx(0.9)
    assert entry.final_score == pytest.approx(0.9)


# §14 No.7 境界値（risk 最大）
def test_run_final_score_calculation_applies_maximum_risk_penalty() -> None:
    context = _single_entry_context(risk_penalty=1.0)

    result, _ = run_scoring_from_context(context)

    entry = result.entries[0]
    assert entry.risk_penalty == pytest.approx(1.0)
    assert entry.pre_rank_score == pytest.approx(0.632)
    assert entry.final_score == pytest.approx(0.632)


# §14 No.8 欠損（popularity）
def test_run_final_score_calculation_fills_missing_popularity_score_with_neutral_value() -> None:
    context = _single_entry_context(popularity_score=None)

    result, _ = run_scoring_from_context(context)

    entry = result.entries[0]
    assert entry.popularity_score == pytest.approx(0.5)
    assert entry.pre_rank_score == pytest.approx(0.678)


# §14 No.9 欠損（risk）
def test_run_final_score_calculation_fills_missing_risk_penalty_with_neutral_value() -> None:
    context = _single_entry_context(risk_penalty=None)

    result, _ = run_scoring_from_context(context)

    entry = result.entries[0]
    assert entry.risk_penalty == pytest.approx(0.0)
    assert entry.pre_rank_score == pytest.approx(0.732)


# §14 No.10 欠損（context・候補単位）
def test_run_final_score_calculation_excludes_candidate_with_missing_context_score() -> None:
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

    result, metrics = run_scoring_from_context(context)

    assert [entry.item_id for entry in result.entries] == ["item-001"]
    assert metrics.final_score_excluded_candidate_count == 1


# §14 No.11 入力 0 件
def test_run_final_score_calculation_succeeds_with_empty_entries_without_grs_rec_012() -> None:
    context = _sample_context(
        risk_penalty_result=RiskPenaltyResult(entries=(), total_scored=0),
    )

    result, metrics = run_scoring_from_context(context)

    assert result.total_scored == 0
    assert result.entries == ()
    assert metrics.final_score_calculator_candidate_count == 0


# §14 No.12 risk_penalty_result 欠損
def test_run_final_score_calculation_raises_grs_rec_012_when_risk_penalty_result_missing() -> None:
    context = _sample_context()
    del context.risk_penalty_result  # type: ignore[attr-defined]

    with pytest.raises(FinalScoreCalculatorError) as exc_info:
        run_scoring_from_context(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.13 JOIN 不整合
def test_run_final_score_calculation_raises_grs_rec_012_for_context_score_join_mismatch() -> None:
    context = _sample_context(
        context_score_result=ContextScoreResult(
            entries=(_context_score_entry(item_id="other-item"),),
            lambda_ctx_applied=0.4,
            total_scored=1,
        ),
    )

    with pytest.raises(FinalScoreCalculatorError) as exc_info:
        run_scoring_from_context(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_run_final_score_calculation_raises_grs_rec_012_for_popularity_score_join_mismatch() -> None:
    context = _sample_context(
        popularity_score_result=PopularityScoreResult(
            entries=(_popularity_score_entry(item_id="other-item"),),
            max_review_count_in_candidates=100,
            total_scored=1,
        ),
    )

    with pytest.raises(FinalScoreCalculatorError) as exc_info:
        run_scoring_from_context(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.14 未対応 formula
def test_run_final_score_calculation_raises_grs_rec_012_for_unsupported_formula() -> None:
    context = _single_entry_context(
        config_versions={
            "ranking_config_id": "rc-1",
            "final_score_formula": "unsupported_formula",
        },
    )

    with pytest.raises(FinalScoreCalculatorError) as exc_info:
        run_final_score_calculation(
            risk_penalty_result=context.risk_penalty_result,  # type: ignore[attr-defined]
            context_score_result=context.context_score_result,
            popularity_score_result=context.popularity_score_result,  # type: ignore[attr-defined]
            config_versions=context.config_versions,
        )

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.16 責務境界
def test_run_final_score_calculation_does_not_emit_ranking_or_mmr_fields() -> None:
    context = _single_entry_context()

    result, _ = run_scoring_from_context(context)

    entry = result.entries[0]
    entry_field_names = {field.name for field in fields(FinalScoreEntry)}
    assert "rank" not in entry_field_names
    assert "mmr_score" not in entry_field_names
    assert "selected" not in entry_field_names
    assert entry.context_score == pytest.approx(0.84)
    assert entry.popularity_score == pytest.approx(0.72)
    assert entry.risk_penalty == pytest.approx(0.10)


# §14 No.19 上流 result 不変
def test_run_final_score_calculation_does_not_mutate_upstream_score_results() -> None:
    context = _sample_context()
    original_context = context.context_score_result
    original_popularity = context.popularity_score_result  # type: ignore[attr-defined]
    original_risk = context.risk_penalty_result  # type: ignore[attr-defined]
    original_context_entries = original_context.entries
    original_popularity_entries = original_popularity.entries
    original_risk_entries = original_risk.entries

    run_scoring_from_context(context)

    assert context.context_score_result is original_context
    assert context.popularity_score_result is original_popularity  # type: ignore[attr-defined]
    assert context.risk_penalty_result is original_risk  # type: ignore[attr-defined]
    assert context.context_score_result.entries == original_context_entries
    assert context.popularity_score_result.entries == original_popularity_entries  # type: ignore[attr-defined]
    assert context.risk_penalty_result.entries == original_risk_entries  # type: ignore[attr-defined]


# §14 No.20 ranking_weights
def test_run_final_score_calculation_applies_configured_ranking_weights() -> None:
    context = _single_entry_context(
        config_versions={
            "ranking_config_id": "rc-custom",
            "final_score_formula": FINAL_SCORE_FORMULA_LINEAR_WEIGHTED_V1,
            "ranking_weights.context": "0.50",
            "ranking_weights.popularity": "0.30",
            "ranking_weights.risk": "0.20",
        },
    )

    result, _ = run_scoring_from_context(context)

    entry = result.entries[0]
    assert entry.ranking_weights_used.w_context == pytest.approx(0.50)
    assert entry.ranking_weights_used.w_popularity == pytest.approx(0.30)
    assert entry.ranking_weights_used.w_risk == pytest.approx(0.20)
    assert entry.score_breakdown["context"]["weight"] == pytest.approx(0.50)
    assert entry.pre_rank_score == pytest.approx(
        0.50 * 0.84 + 0.30 * 0.72 - 0.20 * 0.10,
        rel=1e-5,
    )


def test_run_final_score_calculation_normalizes_ranking_weights_when_sum_deviates() -> None:
    context = _single_entry_context(
        config_versions={
            "ranking_config_id": "rc-normalize",
            "final_score_formula": FINAL_SCORE_FORMULA_LINEAR_WEIGHTED_V1,
            "ranking_weights.context": "0.70",
            "ranking_weights.popularity": "0.20",
            "ranking_weights.risk": "0.20",
        },
    )

    result, _ = run_scoring_from_context(context)

    entry = result.entries[0]
    assert entry.ranking_weights_used.w_context == pytest.approx(0.70 / 1.10, rel=1e-5)
    assert entry.ranking_weights_used.w_popularity == pytest.approx(0.20 / 1.10, rel=1e-5)
    assert entry.ranking_weights_used.w_risk == pytest.approx(0.20 / 1.10, rel=1e-5)


def test_run_final_score_calculation_raises_grs_rec_012_when_ranking_weights_sum_is_non_positive() -> None:
    context = _single_entry_context(
        config_versions={
            "ranking_config_id": "rc-invalid",
            "final_score_formula": FINAL_SCORE_FORMULA_LINEAR_WEIGHTED_V1,
            "ranking_weights.context": "0.0",
            "ranking_weights.popularity": "0.0",
            "ranking_weights.risk": "0.0",
        },
    )

    with pytest.raises(FinalScoreCalculatorError) as exc_info:
        run_scoring_from_context(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
