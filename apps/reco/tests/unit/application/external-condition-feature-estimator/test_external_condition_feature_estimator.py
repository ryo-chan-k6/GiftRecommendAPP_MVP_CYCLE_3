"""MOD-RECO-005 External Condition Feature Estimator smoke tests."""

from __future__ import annotations

import pytest

from conftest import (
    _sample_context,
    build_estimator_with_registered_run,
)
from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
from reco.application.external_condition_feature_estimator import (
    ESTIMATION_METHOD_RULE,
    ExternalFeatureEstimateError,
    SURFACE_ERROR_CODE,
    build_default_feature_rule_repository,
    merge_external_feature_raw,
)
from reco.domain import OccasionCondition, RecommendationRequest, RelationshipCondition


def test_execute_estimates_lover_birthday_with_pair_rule() -> None:
    context = _sample_context()
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.external_feature_estimate
    assert estimate is not None
    assert estimate.relationship_code == "lover"
    assert estimate.occasion_code == "birthday"
    assert estimate.semantic_config_version_id == DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    assert estimate.estimation_method == ESTIMATION_METHOD_RULE
    assert estimate.pair_delta["emotion"] == pytest.approx(0.10)
    assert estimate.external_feature_raw["emotion"] == pytest.approx(
        0.5 * 0.85 + 0.5 * 0.75 + 0.10,
    )
    assert "MOD-RECO-005" in updated.completed_modules


def test_undefined_pair_combination_uses_zero_delta() -> None:
    request = RecommendationRequest(
        request_id="req-no-pair",
        relationship=RelationshipCondition(relationship_code="friend_casual"),
        occasion=OccasionCondition(occasion_code="thanks"),
    )
    context = _sample_context(request=request, run_id="run-no-pair")
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.external_feature_estimate
    assert estimate is not None
    assert all(value == 0.0 for value in estimate.pair_delta.values())
    assert estimate.external_feature_raw["formality"] == pytest.approx(
        0.5 * 0.35 + 0.5 * 0.55,
    )


def test_missing_relationship_rule_raises_grs_rec_005() -> None:
    context = _sample_context()
    rules = build_default_feature_rule_repository()
    rules.relationship_features = {
        key: value
        for key, value in rules.relationship_features.items()
        if key[0] != "lover"
    }
    estimator = build_estimator_with_registered_run(context, feature_rules=rules)

    with pytest.raises(ExternalFeatureEstimateError) as exc_info:
        estimator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_merge_external_feature_raw_matches_spec_formula() -> None:
    axes = (
        "formality",
        "safety",
        "brand_appropriateness",
        "emotion",
        "novelty",
        "intimacy",
        "symbolic_identity",
        "story_richness",
    )
    relationship = {axis: 0.80 for axis in axes}
    occasion = {axis: 0.40 for axis in axes}
    pair_delta = {axis: 0.05 for axis in axes}

    merged = merge_external_feature_raw(relationship, occasion, pair_delta)

    assert merged["formality"] == pytest.approx(0.5 * 0.80 + 0.5 * 0.40 + 0.05)
