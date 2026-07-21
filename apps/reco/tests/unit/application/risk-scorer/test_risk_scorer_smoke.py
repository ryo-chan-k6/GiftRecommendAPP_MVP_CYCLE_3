"""MOD-RECO-018 Risk Scorer smoke tests (implementation Task)."""

from __future__ import annotations

import pytest

from conftest import (
    _feature_match_entry,
    _meaning_match_entry,
    _popularity_score_entry,
    _sample_context,
    _sample_feature_match_result,
    _sample_meaning_match_result,
    _sample_popularity_score_result,
    build_scorer,
)
from reco.application.feature_matcher.models import FeatureMatchResult
from reco.application.meaning_match_aggregator.models import MeaningMatchResult
from reco.application.popularity_scorer.models import PopularityScoreResult
from reco.application.risk_scorer import (
    RISK_FORMULA_AVOID_SOCIAL_DATA_QUALITY_WEIGHTED,
    RiskScorerError,
    SURFACE_ERROR_CODE,
)


def test_execute_calculates_weighted_risk_penalty() -> None:
    context = _sample_context()
    scorer = build_scorer()

    result_context = scorer.execute(context)

    entry = result_context.risk_penalty_result.entries[0]  # type: ignore[attr-defined]
    assert entry.avoid_risk == pytest.approx(0.30)
    assert entry.social_low_risk == pytest.approx(0.25)
    assert entry.item_feature_confidence_used == pytest.approx(0.75)
    assert entry.data_quality_risk == pytest.approx(0.25)
    assert entry.risk_penalty == pytest.approx(
        0.50 * entry.avoid_risk
        + 0.30 * entry.social_low_risk
        + 0.20 * entry.data_quality_risk,
        rel=1e-5,
    )
    assert entry.risk_formula == RISK_FORMULA_AVOID_SOCIAL_DATA_QUALITY_WEIGHTED
    assert result_context.risk_scorer_candidate_count == 1  # type: ignore[attr-defined]
    assert result_context.avoid_risk_nonzero_count == 1  # type: ignore[attr-defined]
    assert "MOD-RECO-018" in result_context.completed_modules


def test_execute_with_empty_popularity_entries_succeeds() -> None:
    context = _sample_context(
        popularity_score_result=PopularityScoreResult(
            entries=(),
            max_review_count_in_candidates=0,
            total_scored=0,
        ),
    )
    scorer = build_scorer()

    result_context = scorer.execute(context)

    result = result_context.risk_penalty_result  # type: ignore[attr-defined]
    assert result.total_scored == 0
    assert result.entries == ()
    assert result_context.risk_scorer_candidate_count == 0  # type: ignore[attr-defined]


def test_execute_preserves_candidate_order() -> None:
    context = _sample_context(
        popularity_score_result=_sample_popularity_score_result(
            entries=(
                _popularity_score_entry(item_id="item-001"),
                _popularity_score_entry(item_id="item-002"),
            ),
        ),
        feature_match_result=_sample_feature_match_result(
            entries=(
                _feature_match_entry(item_id="item-001"),
                _feature_match_entry(item_id="item-002"),
            ),
        ),
        meaning_match_result=_sample_meaning_match_result(
            entries=(
                _meaning_match_entry(item_id="item-001"),
                _meaning_match_entry(item_id="item-002"),
            ),
        ),
    )
    scorer = build_scorer()

    result_context = scorer.execute(context)

    item_ids = [
        entry.item_id
        for entry in result_context.risk_penalty_result.entries  # type: ignore[attr-defined]
    ]
    assert item_ids == ["item-001", "item-002"]


def test_execute_treats_null_avoid_similarity_as_zero_risk() -> None:
    context = _sample_context(
        feature_match_result=_sample_feature_match_result(
            entries=(_feature_match_entry(item_id="item-001", avoid_similarity=None),),
        ),
    )
    scorer = build_scorer()

    result_context = scorer.execute(context)

    entry = result_context.risk_penalty_result.entries[0]  # type: ignore[attr-defined]
    assert entry.avoid_risk == pytest.approx(0.0)
    assert entry.avoid_similarity_used is None
    assert result_context.avoid_risk_nonzero_count == 0  # type: ignore[attr-defined]


def test_execute_does_not_mutate_input_results() -> None:
    context = _sample_context()
    original_popularity = context.popularity_score_result  # type: ignore[attr-defined]
    original_feature = context.feature_match_result
    original_meaning = context.meaning_match_result
    scorer = build_scorer()

    scorer.execute(context)

    assert context.popularity_score_result is original_popularity  # type: ignore[attr-defined]
    assert context.feature_match_result is original_feature
    assert context.meaning_match_result is original_meaning


def test_execute_raises_when_popularity_score_result_missing() -> None:
    context = _sample_context()
    del context.popularity_score_result  # type: ignore[attr-defined]
    scorer = build_scorer()

    with pytest.raises(RiskScorerError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_when_feature_match_result_missing() -> None:
    context = _sample_context()
    context.feature_match_result = None
    scorer = build_scorer()

    with pytest.raises(RiskScorerError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_for_join_mismatch() -> None:
    context = _sample_context(
        feature_match_result=FeatureMatchResult(
            entries=(_feature_match_entry(item_id="other-item"),),
            total_matched=1,
            total_excluded=0,
        ),
    )
    scorer = build_scorer()

    with pytest.raises(RiskScorerError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_for_unsupported_risk_formula() -> None:
    config_versions = {
        "ranking_config_id": "rc-1",
        "risk_formula": "unsupported_formula",
    }
    context = _sample_context(config_versions=config_versions)
    scorer = build_scorer()

    with pytest.raises(RiskScorerError) as exc_info:
        scorer.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
