"""MOD-RECO-005 External Condition Feature Estimator unit tests (module spec §14)."""

from __future__ import annotations

import json
from dataclasses import fields

import pytest

from conftest import (
    BIRTHDAY_OCCASION_FEATURES,
    BOSS_RELATIONSHIP_FEATURES,
    OTHER_OCCASION_FEATURES,
    OTHER_RELATIONSHIP_FEATURES,
    _request_with_codes,
    _sample_context,
    build_estimator_with_registered_run,
)
from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
from reco.application.external_condition_feature_estimator import (
    ESTIMATION_METHOD_RULE,
    ExternalFeatureEstimate,
    ExternalFeatureEstimateError,
    SURFACE_ERROR_CODE,
    build_default_feature_rule_repository,
    merge_external_feature_raw,
)
from reco.domain import (
    OccasionCondition,
    RecommendationRequest,
    RelationshipCondition,
)
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES
from reco.domain.semantic_extraction import ExtractedSemanticConcept, SemanticExtractionResult
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


def _assert_feature_vector(actual: dict[str, float], expected: dict[str, float]) -> None:
    for axis in MVP_FEATURE_CODES:
        assert actual[axis] == pytest.approx(expected[axis])


# §14 No.1 正常系（代表 relationship）
def test_boss_relationship_features_match_rule_repository() -> None:
    request = _request_with_codes("boss", "thanks", request_id="req-boss")
    context = _sample_context(request=request, run_id="run-boss")
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.external_feature_estimate
    assert estimate is not None
    _assert_feature_vector(estimate.relationship_feature, BOSS_RELATIONSHIP_FEATURES)
    assert estimate.relationship_code == "boss"


# §14 No.2 正常系（代表 occasion）
def test_birthday_occasion_features_match_rule_repository() -> None:
    context = _sample_context(run_id="run-birthday")
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.external_feature_estimate
    assert estimate is not None
    _assert_feature_vector(estimate.occasion_feature, BIRTHDAY_OCCASION_FEATURES)
    assert estimate.occasion_code == "birthday"


# §14 No.3 正常系（Pair 適用）
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


# §14 No.4 正常系（Pair 未定義）
def test_undefined_pair_combination_uses_zero_delta() -> None:
    request = _request_with_codes("friend_casual", "thanks", request_id="req-no-pair")
    context = _sample_context(request=request, run_id="run-no-pair")
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.external_feature_estimate
    assert estimate is not None
    assert all(value == 0.0 for value in estimate.pair_delta.values())
    assert estimate.external_feature_raw["formality"] == pytest.approx(
        0.5 * 0.35 + 0.5 * 0.55,
    )


# §14 No.5 統合式
def test_merge_external_feature_raw_matches_spec_formula() -> None:
    axes = MVP_FEATURE_CODES
    relationship = {axis: 0.80 for axis in axes}
    occasion = {axis: 0.40 for axis in axes}
    pair_delta = {axis: 0.05 for axis in axes}

    merged = merge_external_feature_raw(relationship, occasion, pair_delta)

    assert merged["formality"] == pytest.approx(0.5 * 0.80 + 0.5 * 0.40 + 0.05)


# §14 No.6 境界値（other × other）
def test_other_other_pair_uses_relationship_and_occasion_baseline_only() -> None:
    request = _request_with_codes("other", "other", request_id="req-other-other")
    context = _sample_context(request=request, run_id="run-other-other")
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.external_feature_estimate
    assert estimate is not None
    _assert_feature_vector(estimate.relationship_feature, OTHER_RELATIONSHIP_FEATURES)
    _assert_feature_vector(estimate.occasion_feature, OTHER_OCCASION_FEATURES)
    assert all(value == 0.0 for value in estimate.pair_delta.values())
    assert estimate.external_feature_raw["formality"] == pytest.approx(
        0.5 * OTHER_RELATIONSHIP_FEATURES["formality"]
        + 0.5 * OTHER_OCCASION_FEATURES["formality"],
    )


# §14 No.7 version 整合
def test_execute_sets_semantic_config_version_id_from_execution_context() -> None:
    context = _sample_context(run_id="run-version")
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.external_feature_estimate
    assert estimate is not None
    assert estimate.semantic_config_version_id == context.config_versions[
        "semantic_config_version_id"
    ]
    assert estimate.semantic_config_version_id == DEFAULT_SEMANTIC_CONFIG_VERSION_ID


# §14 No.8 例外系（Rule 欠落）— relationship
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


# §14 No.8 例外系（Rule 欠落）— occasion
def test_missing_occasion_rule_raises_grs_rec_005() -> None:
    context = _sample_context()
    rules = build_default_feature_rule_repository()
    rules.occasion_features = {
        key: value
        for key, value in rules.occasion_features.items()
        if key[0] != "birthday"
    }
    estimator = build_estimator_with_registered_run(context, feature_rules=rules)

    with pytest.raises(ExternalFeatureEstimateError) as exc_info:
        estimator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.9 例外系（Run 不整合）— version 不一致
def test_execute_raises_when_run_version_mismatch() -> None:
    context = _sample_context(run_id="run-mismatch")
    estimator = build_estimator_with_registered_run(context)
    estimator.run_validation.register_run("run-mismatch", "other-version")

    with pytest.raises(ExternalFeatureEstimateError) as exc_info:
        estimator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.9 例外系（Run 不整合）— Run 未存在
def test_execute_raises_when_recommendation_run_not_found() -> None:
    context = _sample_context(run_id="run-missing")
    estimator = build_estimator_with_registered_run(context, register_run=False)

    with pytest.raises(ExternalFeatureEstimateError) as exc_info:
        estimator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "not found" in exc_info.value.message


# §14 No.10 例外系（入力欠落）— relationship 欠落
def test_execute_raises_when_relationship_is_missing() -> None:
    request = RecommendationRequest(
        request_id="req-no-relationship",
        occasion=OccasionCondition(occasion_code="birthday"),
    )
    context = _sample_context(request=request, run_id="run-no-relationship")
    estimator = build_estimator_with_registered_run(context)

    with pytest.raises(ExternalFeatureEstimateError) as exc_info:
        estimator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.10 例外系（入力欠落）— occasion 欠落
def test_execute_raises_when_occasion_is_missing() -> None:
    request = RecommendationRequest(
        request_id="req-no-occasion",
        relationship=RelationshipCondition(relationship_code="lover"),
    )
    context = _sample_context(request=request, run_id="run-no-occasion")
    estimator = build_estimator_with_registered_run(context)

    with pytest.raises(ExternalFeatureEstimateError) as exc_info:
        estimator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.11 Semantic 非代替
def test_semantic_extraction_result_does_not_override_rule_based_estimate() -> None:
    context = _sample_context(run_id="run-semantic-non-override")
    context.semantic_extraction_result = SemanticExtractionResult(
        concepts=(
            ExtractedSemanticConcept(
                concept_code="warm_heartfelt",
                confidence=0.99,
                input_intent="prefer",
                extraction_method="rule",
                source_type="preferred_text",
            ),
        ),
        hard_filter_candidates=(),
        user_semantic_id="us-semantic-1",
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
    )
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.external_feature_estimate
    assert estimate is not None
    assert estimate.external_feature_raw["emotion"] == pytest.approx(
        0.5 * 0.85 + 0.5 * 0.75 + 0.10,
    )


# §14 No.12 DB 非永続化
def test_execute_does_not_persist_user_feature_or_mutate_rule_repository() -> None:
    context = _sample_context(run_id="run-no-db")
    rules = build_default_feature_rule_repository()
    relationship_snapshot = dict(rules.relationship_features)
    occasion_snapshot = dict(rules.occasion_features)
    pair_snapshot = dict(rules.pair_deltas)
    estimator = build_estimator_with_registered_run(context, feature_rules=rules)
    run_versions_before = dict(estimator.run_validation.run_versions)
    estimator_field_names = {field.name for field in fields(estimator)}

    updated = estimator.execute(context)

    assert updated.external_feature_estimate is not None
    assert estimator.run_validation.run_versions == run_versions_before
    assert rules.relationship_features == relationship_snapshot
    assert rules.occasion_features == occasion_snapshot
    assert rules.pair_deltas == pair_snapshot
    assert "user_feature" not in estimator_field_names


# §14 No.14 ログ — trace_id を含み secret を含まない
def test_execute_emits_structured_log_with_trace_id_without_secrets() -> None:
    context = _sample_context(run_id="run-log")
    logger = ScaffoldRecoLogger()
    estimator = build_estimator_with_registered_run(context, logger=logger)

    estimator.execute(context)

    completion_logs = [
        record
        for record in logger.records
        if record.event == "external_feature_estimation_completed"
    ]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == context.trace_id
    assert log_record.context.run_id == "run-log"
    serialized = json.dumps(log_record.attributes, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert "password" not in serialized
    assert "token" not in serialized


# §14 No.16 出力受け渡し
def test_execute_attaches_external_feature_estimate_to_execution_context() -> None:
    context = _sample_context(run_id="run-handoff")
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.external_feature_estimate
    assert isinstance(estimate, ExternalFeatureEstimate)
    assert estimate.relationship_code == "lover"
    assert estimate.occasion_code == "birthday"
    assert set(estimate.external_feature_raw) == set(MVP_FEATURE_CODES)
    assert set(estimate.relationship_feature) == set(MVP_FEATURE_CODES)
    assert set(estimate.occasion_feature) == set(MVP_FEATURE_CODES)
    assert set(estimate.pair_delta) == set(MVP_FEATURE_CODES)
