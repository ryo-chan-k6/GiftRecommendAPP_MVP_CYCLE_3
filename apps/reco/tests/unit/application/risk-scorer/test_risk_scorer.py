"""MOD-RECO-018 Risk Scorer unit tests (module spec §14 unit)."""

from __future__ import annotations

from dataclasses import fields

import pytest

from conftest import (
    _feature_match_entry,
    _meaning_match_entry,
    _popularity_score_entry,
    _sample_context,
    _sample_feature_match_result,
    _sample_meaning_match_result,
    _sample_popularity_score_result,
    run_scoring_from_context,
)
from reco.application.feature_matcher.models import FeatureMatchResult
from reco.application.meaning_match_aggregator.models import MeaningMatchResult
from reco.application.popularity_scorer.models import PopularityScoreResult
from reco.application.risk_scorer import (
    RISK_FORMULA_AVOID_SOCIAL_DATA_QUALITY_WEIGHTED,
    RiskScorerError,
    SURFACE_ERROR_CODE,
    run_risk_scoring,
)
from reco.application.risk_scorer.models import RiskPenaltyEntry
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES


def _single_entry_context(
    *,
    avoid_similarity: float | None = 0.30,
    social_match: float = 0.45,
    imputed_axes: tuple[str, ...] = ("formality", "safety"),
) -> tuple:
    context = _sample_context(
        popularity_score_result=_sample_popularity_score_result(
            entries=(_popularity_score_entry(item_id="item-001"),),
        ),
        feature_match_result=_sample_feature_match_result(
            entries=(
                _feature_match_entry(
                    item_id="item-001",
                    avoid_similarity=avoid_similarity,
                    imputed_axes=imputed_axes,
                ),
            ),
        ),
        meaning_match_result=_sample_meaning_match_result(
            entries=(_meaning_match_entry(item_id="item-001", social_match=social_match),),
        ),
    )
    return context


# §14 No.1 正常系（基本算出）
def test_run_risk_scoring_matches_ranking_definition_example() -> None:
    context = _single_entry_context()

    result, metrics = run_scoring_from_context(context)

    entry = result.entries[0]
    assert entry.avoid_risk == pytest.approx(0.30)
    assert entry.social_low_risk == pytest.approx(0.25)
    assert entry.item_feature_confidence_used == pytest.approx(0.75)
    assert entry.data_quality_risk == pytest.approx(0.25)
    assert entry.risk_penalty == pytest.approx(0.275, rel=1e-5)
    assert entry.risk_formula == RISK_FORMULA_AVOID_SOCIAL_DATA_QUALITY_WEIGHTED
    assert metrics.risk_scorer_candidate_count == 1


# §14 No.2 正常系（avoid 高）
def test_run_risk_scoring_increases_risk_penalty_for_high_avoid_similarity() -> None:
    baseline_context = _single_entry_context(avoid_similarity=0.30)
    high_avoid_context = _single_entry_context(avoid_similarity=0.90)

    baseline_result, _ = run_scoring_from_context(baseline_context)
    high_avoid_result, metrics = run_scoring_from_context(high_avoid_context)

    assert high_avoid_result.entries[0].avoid_risk == pytest.approx(0.90)
    assert high_avoid_result.entries[0].risk_penalty > baseline_result.entries[0].risk_penalty
    assert metrics.avoid_risk_nonzero_count == 1


# §14 No.3 正常系（social 低）
def test_run_risk_scoring_increases_social_low_risk_for_low_social_match() -> None:
    context = _single_entry_context(social_match=0.10)

    result, _ = run_scoring_from_context(context)

    entry = result.entries[0]
    assert entry.social_match_used == pytest.approx(0.10)
    assert entry.social_low_risk == pytest.approx((0.60 - 0.10) / 0.60, rel=1e-5)
    assert entry.risk_penalty == pytest.approx(
        0.50 * entry.avoid_risk
        + 0.30 * entry.social_low_risk
        + 0.20 * entry.data_quality_risk,
        rel=1e-5,
    )


# §14 No.4 正常系（confidence 低）
def test_run_risk_scoring_increases_data_quality_risk_when_all_axes_imputed() -> None:
    context = _single_entry_context(imputed_axes=MVP_FEATURE_CODES)

    result, metrics = run_scoring_from_context(context)

    entry = result.entries[0]
    assert entry.item_feature_confidence_used == pytest.approx(0.0)
    assert entry.data_quality_risk == pytest.approx(1.0)
    assert entry.risk_penalty == pytest.approx(
        0.50 * entry.avoid_risk + 0.30 * entry.social_low_risk + 0.20,
        rel=1e-5,
    )
    assert metrics.risk_missing_signal_count == 0


# §14 No.5 正常系（候補複数）
def test_run_risk_scoring_preserves_candidate_input_order() -> None:
    context = _sample_context(
        popularity_score_result=_sample_popularity_score_result(
            entries=(
                _popularity_score_entry(item_id="item-a"),
                _popularity_score_entry(item_id="item-b"),
                _popularity_score_entry(item_id="item-c"),
            ),
        ),
        feature_match_result=_sample_feature_match_result(
            entries=(
                _feature_match_entry(item_id="item-a"),
                _feature_match_entry(item_id="item-b"),
                _feature_match_entry(item_id="item-c"),
            ),
        ),
        meaning_match_result=_sample_meaning_match_result(
            entries=(
                _meaning_match_entry(item_id="item-a"),
                _meaning_match_entry(item_id="item-b"),
                _meaning_match_entry(item_id="item-c"),
            ),
        ),
    )

    result, metrics = run_scoring_from_context(context)

    assert [entry.item_id for entry in result.entries] == ["item-a", "item-b", "item-c"]
    assert result.total_scored == 3
    assert metrics.risk_scorer_candidate_count == 3


# §14 No.6 境界値（avoid 省略）
def test_run_risk_scoring_treats_null_avoid_similarity_as_zero_risk() -> None:
    context = _single_entry_context(avoid_similarity=None)

    result, metrics = run_scoring_from_context(context)

    entry = result.entries[0]
    assert entry.avoid_risk == pytest.approx(0.0)
    assert entry.avoid_similarity_used is None
    assert metrics.avoid_risk_nonzero_count == 0


# §14 No.7 境界値（social 閾値）
def test_run_risk_scoring_sets_social_low_risk_to_zero_at_threshold() -> None:
    context = _single_entry_context(social_match=0.60)

    result, _ = run_scoring_from_context(context)

    entry = result.entries[0]
    assert entry.social_low_risk == pytest.approx(0.0)
    assert entry.social_match_used == pytest.approx(0.60)


# §14 No.8 境界値（social 閾値下）
def test_run_risk_scoring_calculates_social_low_risk_below_threshold() -> None:
    context = _single_entry_context(social_match=0.30)

    result, _ = run_scoring_from_context(context)

    entry = result.entries[0]
    assert entry.social_low_risk == pytest.approx(0.50, rel=1e-5)


# §14 No.9 境界値（confidence 欠損）
def test_run_risk_scoring_uses_default_confidence_when_feature_axes_missing() -> None:
    context = _sample_context(
        feature_match_result=_sample_feature_match_result(
            entries=(_feature_match_entry(item_id="item-001", features={}),),
        ),
    )

    result, metrics = run_scoring_from_context(context)

    entry = result.entries[0]
    assert entry.item_feature_confidence_used == pytest.approx(0.5)
    assert entry.data_quality_risk == pytest.approx(0.5)
    assert entry.signal_missing is True
    assert metrics.risk_missing_signal_count == 1


# §14 No.10 imputed 代理
def test_run_risk_scoring_derives_confidence_from_imputed_axes() -> None:
    context = _single_entry_context(imputed_axes=("formality", "safety"))

    result, _ = run_scoring_from_context(context)

    entry = result.entries[0]
    assert entry.item_feature_confidence_used == pytest.approx(0.75)
    assert entry.signal_missing is False


# §14 No.11 入力 0 件
def test_run_risk_scoring_succeeds_with_empty_entries_without_grs_rec_012() -> None:
    context = _sample_context(
        popularity_score_result=PopularityScoreResult(
            entries=(),
            max_review_count_in_candidates=0,
            total_scored=0,
        ),
    )

    result, metrics = run_scoring_from_context(context)

    assert result.total_scored == 0
    assert result.entries == ()
    assert metrics.risk_scorer_candidate_count == 0


# §14 No.13 JOIN 不整合
def test_run_risk_scoring_raises_grs_rec_012_for_feature_match_join_mismatch() -> None:
    context = _sample_context(
        feature_match_result=FeatureMatchResult(
            entries=(_feature_match_entry(item_id="other-item"),),
            total_matched=1,
            total_excluded=0,
        ),
    )

    with pytest.raises(RiskScorerError) as exc_info:
        run_scoring_from_context(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_run_risk_scoring_raises_grs_rec_012_for_meaning_match_join_mismatch() -> None:
    context = _sample_context(
        meaning_match_result=MeaningMatchResult(
            entries=(_meaning_match_entry(item_id="other-item"),),
            total_aggregated=1,
        ),
    )

    with pytest.raises(RiskScorerError) as exc_info:
        run_scoring_from_context(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.14 未対応 formula
def test_run_risk_scoring_raises_grs_rec_012_for_unsupported_formula() -> None:
    context = _sample_context(
        config_versions={
            "ranking_config_id": "rc-1",
            "risk_formula": "unsupported_formula",
        },
    )

    with pytest.raises(RiskScorerError) as exc_info:
        run_risk_scoring(
            popularity_score_result=context.popularity_score_result,  # type: ignore[attr-defined]
            feature_match_result=context.feature_match_result,
            meaning_match_result=context.meaning_match_result,
            config_versions=context.config_versions,
        )

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.16 責務境界
def test_run_risk_scoring_does_not_emit_final_score_or_ranking_fields() -> None:
    context = _single_entry_context(avoid_similarity=0.30)

    result, _ = run_scoring_from_context(context)

    entry = result.entries[0]
    entry_field_names = {field.name for field in fields(RiskPenaltyEntry)}
    assert "final_score" not in entry_field_names
    assert "popularity_score" not in entry_field_names
    assert "context_score" not in entry_field_names
    assert "rank" not in entry_field_names
    assert entry.risk_penalty is not None
    # avoid は Matching 出力をそのまま利用し、独立再算出しない。
    assert entry.avoid_similarity_used == pytest.approx(0.30)
    assert entry.avoid_risk == entry.avoid_similarity_used


# §14 No.19 入力 result 不変
def test_run_risk_scoring_does_not_mutate_matching_or_popularity_results() -> None:
    context = _sample_context()
    original_popularity = context.popularity_score_result  # type: ignore[attr-defined]
    original_feature = context.feature_match_result
    original_meaning = context.meaning_match_result
    original_popularity_entries = original_popularity.entries
    original_feature_entries = original_feature.entries
    original_meaning_entries = original_meaning.entries

    run_scoring_from_context(context)

    assert context.popularity_score_result is original_popularity  # type: ignore[attr-defined]
    assert context.feature_match_result is original_feature
    assert context.meaning_match_result is original_meaning
    assert context.popularity_score_result.entries == original_popularity_entries  # type: ignore[attr-defined]
    assert context.feature_match_result.entries == original_feature_entries
    assert context.meaning_match_result.entries == original_meaning_entries


# §14 No.20 clip
def test_run_risk_scoring_clips_out_of_range_inputs_and_penalty_to_unit_interval() -> None:
    context = _single_entry_context(avoid_similarity=1.5, social_match=-0.2)
    context.config_versions = {
        "ranking_config_id": "rc-clip",
        "risk_formula": RISK_FORMULA_AVOID_SOCIAL_DATA_QUALITY_WEIGHTED,
        "risk_weights.avoid": "0.80",
        "risk_weights.social": "0.80",
        "risk_weights.data_quality": "0.80",
    }

    result, metrics = run_scoring_from_context(context)

    entry = result.entries[0]
    assert entry.avoid_similarity_used == pytest.approx(1.0)
    assert entry.social_match_used == pytest.approx(0.0)
    assert 0.0 <= entry.risk_penalty <= 1.0
    assert entry.risk_penalty == pytest.approx(1.0)
    assert metrics.risk_penalty_value_out_of_range_count >= 1


def test_run_risk_scoring_raises_when_total_scored_is_inconsistent() -> None:
    context = _sample_context(
        popularity_score_result=PopularityScoreResult(
            entries=(_popularity_score_entry(item_id="item-001"),),
            max_review_count_in_candidates=100,
            total_scored=99,
        ),
    )

    with pytest.raises(RiskScorerError) as exc_info:
        run_risk_scoring(
            popularity_score_result=context.popularity_score_result,  # type: ignore[attr-defined]
            feature_match_result=context.feature_match_result,
            meaning_match_result=context.meaning_match_result,
            config_versions=context.config_versions,
        )

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
