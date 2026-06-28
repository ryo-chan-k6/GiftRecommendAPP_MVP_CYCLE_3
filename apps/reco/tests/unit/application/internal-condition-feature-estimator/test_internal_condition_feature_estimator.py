"""MOD-RECO-006 Internal Condition Feature Estimator unit tests (module spec §14)."""

from __future__ import annotations

import json
from dataclasses import fields

import pytest

from conftest import (
    _request_with_codes,
    _sample_context,
    build_estimator_with_registered_run,
)
from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
from reco.application.internal_condition_feature_estimator import (
    ESTIMATION_METHOD_RULE,
    InternalFeatureEstimate,
    InternalFeatureEstimateError,
    SURFACE_ERROR_CODE,
    build_default_concept_feature_rule_repository,
    merge_internal_feature_delta,
    zero_feature_vector,
)
from reco.domain import NonPreferredCondition, PreferredCondition, RecommendationRequest
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES
from reco.domain.semantic_extraction import (
    ExtractedSemanticConcept,
    HardFilterCandidate,
    SemanticExtractionResult,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


def _empty_extraction_result() -> SemanticExtractionResult:
    return SemanticExtractionResult(
        concepts=(),
        hard_filter_candidates=(),
        user_semantic_id="us-1",
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
    )


def _extraction_with_concepts(
    *concepts: ExtractedSemanticConcept,
    hard_filter_candidates: tuple[HardFilterCandidate, ...] = (),
) -> SemanticExtractionResult:
    return SemanticExtractionResult(
        concepts=concepts,
        hard_filter_candidates=hard_filter_candidates,
        user_semantic_id="us-1",
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
    )


def _assert_feature_vector(actual: dict[str, float], expected: dict[str, float]) -> None:
    for axis in MVP_FEATURE_CODES:
        assert actual[axis] == pytest.approx(expected[axis])


# §14 No.1 正常系（preferred）
def test_preferred_condition_concept_applies_to_preferred_delta() -> None:
    extraction = _extraction_with_concepts(
        ExtractedSemanticConcept(
            concept_code="formal_refined",
            confidence=0.88,
            input_intent="prefer",
            extraction_method="rule",
            source_type="preferred_condition",
        ),
    )
    context = _sample_context(
        run_id="run-preferred",
        semantic_extraction_result=extraction,
    )
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.internal_feature_estimate
    assert estimate is not None
    assert estimate.preferred_delta["formality"] == pytest.approx(0.25 * 0.88)
    assert estimate.avoid_delta["formality"] == pytest.approx(0.0)
    assert estimate.internal_feature_delta["formality"] == pytest.approx(0.25 * 0.88)
    assert estimate.applied_concept_count == 1
    assert estimate.estimation_method == ESTIMATION_METHOD_RULE
    assert "MOD-RECO-006" in updated.completed_modules


# §14 No.2 正常系（non_preferred）
def test_non_preferred_condition_inverts_positive_rule_into_avoid_delta() -> None:
    extraction = _extraction_with_concepts(
        ExtractedSemanticConcept(
            concept_code="prestigious_quality",
            confidence=0.75,
            input_intent="avoid",
            extraction_method="rule",
            source_type="non_preferred_condition",
        ),
    )
    context = _sample_context(
        run_id="run-avoid",
        semantic_extraction_result=extraction,
    )
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.internal_feature_estimate
    assert estimate is not None
    expected = -0.20 * 0.75
    assert estimate.avoid_delta["formality"] == pytest.approx(expected)
    assert estimate.preferred_delta["formality"] == pytest.approx(0.0)
    assert estimate.internal_feature_delta["formality"] == pytest.approx(expected)


# §14 No.3 正常系（free_text）
def test_free_text_applies_free_text_weight() -> None:
    extraction = _extraction_with_concepts(
        ExtractedSemanticConcept(
            concept_code="emotional_warm",
            confidence=0.80,
            input_intent="prefer",
            extraction_method="llm",
            source_type="free_text",
        ),
    )
    context = _sample_context(
        run_id="run-free-text",
        semantic_extraction_result=extraction,
    )
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.internal_feature_estimate
    assert estimate is not None
    assert estimate.free_text_delta["emotion"] == pytest.approx(0.30 * 0.80 * 0.70)


# §14 No.4 正常系（統合式）
def test_execute_computes_internal_feature_delta_from_all_source_types() -> None:
    extraction = _extraction_with_concepts(
        ExtractedSemanticConcept(
            concept_code="formal_refined",
            confidence=0.80,
            input_intent="prefer",
            extraction_method="rule",
            source_type="preferred_condition",
        ),
        ExtractedSemanticConcept(
            concept_code="prestigious_quality",
            confidence=0.70,
            input_intent="avoid",
            extraction_method="rule",
            source_type="non_preferred_condition",
        ),
        ExtractedSemanticConcept(
            concept_code="emotional_warm",
            confidence=0.75,
            input_intent="prefer",
            extraction_method="llm",
            source_type="free_text",
        ),
    )
    context = _sample_context(
        run_id="run-integration",
        semantic_extraction_result=extraction,
    )
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.internal_feature_estimate
    assert estimate is not None
    expected = merge_internal_feature_delta(
        estimate.preferred_delta,
        estimate.avoid_delta,
        estimate.free_text_delta,
    )
    _assert_feature_vector(estimate.internal_feature_delta, expected)


def test_merge_internal_feature_delta_matches_spec_formula() -> None:
    axes = MVP_FEATURE_CODES
    preferred = {axis: 0.20 for axis in axes}
    avoid = {axis: -0.10 for axis in axes}
    free_text = {axis: 0.05 for axis in axes}

    merged = merge_internal_feature_delta(preferred, avoid, free_text)

    assert merged["formality"] == pytest.approx(0.20 - 0.10 + 0.05)


# §14 No.5 正常系（複数 Concept 加算）
def test_multiple_concepts_accumulate_on_same_axis() -> None:
    extraction = _extraction_with_concepts(
        ExtractedSemanticConcept(
            concept_code="formal_refined",
            confidence=0.80,
            input_intent="prefer",
            extraction_method="rule",
            source_type="preferred_condition",
        ),
        ExtractedSemanticConcept(
            concept_code="prestigious_quality",
            confidence=0.75,
            input_intent="prefer",
            extraction_method="rule",
            source_type="preferred_condition",
        ),
    )
    context = _sample_context(
        run_id="run-multi-concept",
        semantic_extraction_result=extraction,
    )
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.internal_feature_estimate
    assert estimate is not None
    expected_formality = (0.25 * 0.80) + (0.20 * 0.75)
    assert estimate.preferred_delta["formality"] == pytest.approx(expected_formality)
    assert estimate.applied_concept_count == 2


# §14 No.6 境界値（Concept 0 件）
def test_empty_internal_concepts_produce_zero_deltas() -> None:
    context = _sample_context(
        run_id="run-empty",
        semantic_extraction_result=_empty_extraction_result(),
    )
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.internal_feature_estimate
    assert estimate is not None
    assert all(value == 0.0 for value in estimate.internal_feature_delta.values())
    assert estimate.applied_concept_count == 0


# §14 No.7 境界値（confidence 閾値）
def test_low_confidence_concept_is_skipped() -> None:
    extraction = _extraction_with_concepts(
        ExtractedSemanticConcept(
            concept_code="formal_refined",
            confidence=0.59,
            input_intent="prefer",
            extraction_method="rule",
            source_type="preferred_condition",
        ),
    )
    context = _sample_context(
        run_id="run-low-confidence",
        semantic_extraction_result=extraction,
    )
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.internal_feature_estimate
    assert estimate is not None
    assert all(value == 0.0 for value in estimate.preferred_delta.values())
    assert estimate.applied_concept_count == 0


# §14 No.8 境界値（稀疏 Rule）
def test_sparse_rule_missing_axes_contribute_zero() -> None:
    extraction = _extraction_with_concepts(
        ExtractedSemanticConcept(
            concept_code="formal_refined",
            confidence=0.85,
            input_intent="prefer",
            extraction_method="rule",
            source_type="preferred_condition",
        ),
    )
    context = _sample_context(
        run_id="run-sparse",
        semantic_extraction_result=extraction,
    )
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.internal_feature_estimate
    assert estimate is not None
    assert estimate.preferred_delta["formality"] == pytest.approx(0.25 * 0.85)
    assert estimate.preferred_delta["emotion"] == pytest.approx(0.0)
    assert estimate.applied_concept_count == 1


# §14 No.9 否定 Concept
def test_not_too_safe_preferred_applies_negative_polarity_without_inversion() -> None:
    extraction = _extraction_with_concepts(
        ExtractedSemanticConcept(
            concept_code="not_too_safe",
            confidence=0.80,
            input_intent="prefer",
            extraction_method="rule",
            source_type="preferred_condition",
        ),
    )
    context = _sample_context(
        run_id="run-not-too-safe",
        semantic_extraction_result=extraction,
    )
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.internal_feature_estimate
    assert estimate is not None
    assert estimate.preferred_delta["safety"] == pytest.approx(-0.25 * 0.80)
    assert estimate.preferred_delta["novelty"] == pytest.approx(0.20 * 0.80)


# §14 No.10 version 整合
def test_execute_sets_semantic_config_version_id_from_execution_context() -> None:
    context = _sample_context(
        run_id="run-version",
        semantic_extraction_result=_empty_extraction_result(),
    )
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.internal_feature_estimate
    assert estimate is not None
    assert estimate.semantic_config_version_id == context.config_versions[
        "semantic_config_version_id"
    ]
    assert estimate.semantic_config_version_id == DEFAULT_SEMANTIC_CONFIG_VERSION_ID


# §14 No.11 例外系（Run 不整合）— version 不一致
def test_execute_raises_when_run_version_mismatch() -> None:
    context = _sample_context(
        run_id="run-mismatch",
        semantic_extraction_result=_empty_extraction_result(),
    )
    estimator = build_estimator_with_registered_run(context)
    estimator.run_validation.register_run("run-mismatch", "other-version")

    with pytest.raises(InternalFeatureEstimateError) as exc_info:
        estimator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.11 例外系（Run 不整合）— Run 未存在
def test_execute_raises_when_run_is_not_registered() -> None:
    context = _sample_context(
        run_id="run-missing",
        semantic_extraction_result=_empty_extraction_result(),
    )
    estimator = build_estimator_with_registered_run(context, register_run=False)

    with pytest.raises(InternalFeatureEstimateError) as exc_info:
        estimator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "not found" in exc_info.value.message


# §14 No.12 例外系（入力欠落）
def test_execute_raises_when_semantic_extraction_result_is_missing() -> None:
    context = _sample_context(run_id="run-no-semantic")
    estimator = build_estimator_with_registered_run(context)

    with pytest.raises(InternalFeatureEstimateError) as exc_info:
        estimator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.13 例外系（DB 失敗）
def test_execute_raises_when_rule_lookup_fails() -> None:
    extraction = _extraction_with_concepts(
        ExtractedSemanticConcept(
            concept_code="formal_refined",
            confidence=0.90,
            input_intent="prefer",
            extraction_method="rule",
            source_type="preferred_condition",
        ),
    )
    context = _sample_context(
        run_id="run-db-fail",
        semantic_extraction_result=extraction,
    )
    from reco.application.internal_condition_feature_estimator import (
        InMemoryConceptFeatureRuleRepository,
    )

    failing_rules = InMemoryConceptFeatureRuleRepository(should_fail_on_lookup=True)
    estimator = build_estimator_with_registered_run(
        context,
        concept_feature_rules=failing_rules,
    )

    with pytest.raises(InternalFeatureEstimateError) as exc_info:
        estimator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "lookup failed" in exc_info.value.message


# §14 No.14 ng 非混入 — ng_condition
def test_ng_condition_source_type_is_excluded_from_delta_calculation() -> None:
    extraction = _extraction_with_concepts(
        ExtractedSemanticConcept(
            concept_code="alcohol_ng",
            confidence=0.99,
            input_intent="avoid",
            extraction_method="rule",
            source_type="ng_condition",
        ),
    )
    context = _sample_context(
        run_id="run-ng",
        semantic_extraction_result=extraction,
    )
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.internal_feature_estimate
    assert estimate is not None
    assert estimate.applied_concept_count == 0
    assert estimate.internal_feature_delta == zero_feature_vector()


# §14 No.14 ng 非混入 — hard_filter_candidates
def test_hard_filter_candidates_do_not_affect_delta_calculation() -> None:
    extraction = _extraction_with_concepts(
        hard_filter_candidates=(
            HardFilterCandidate(
                filter_type="category",
                filter_value="alcohol",
                evidence_text="お酒は避けたい",
                confidence=0.95,
                source_type="ng_condition",
            ),
        ),
    )
    context = _sample_context(
        run_id="run-hard-filter",
        semantic_extraction_result=extraction,
    )
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.internal_feature_estimate
    assert estimate is not None
    assert estimate.applied_concept_count == 0
    assert estimate.internal_feature_delta == zero_feature_vector()


# §14 No.15 Semantic 非再抽出
def test_request_text_change_does_not_alter_estimate_when_semantic_result_unchanged() -> None:
    extraction = _extraction_with_concepts(
        ExtractedSemanticConcept(
            concept_code="formal_refined",
            confidence=0.85,
            input_intent="prefer",
            extraction_method="rule",
            source_type="preferred_condition",
        ),
    )
    request_a = RecommendationRequest(
        request_id="req-a",
        relationship=_request_with_codes("lover", "birthday").relationship,
        occasion=_request_with_codes("lover", "birthday").occasion,
        preferred_condition=PreferredCondition(preferred_text="フォーマルなもの"),
    )
    request_b = RecommendationRequest(
        request_id="req-b",
        relationship=_request_with_codes("lover", "birthday").relationship,
        occasion=_request_with_codes("lover", "birthday").occasion,
        preferred_condition=PreferredCondition(preferred_text="全く別の希望テキスト"),
        non_preferred_condition=NonPreferredCondition(
            non_preferred_text="避けたい特徴",
        ),
        free_text="追加の自由記述",
    )
    context_a = _sample_context(
        request=request_a,
        run_id="run-request-a",
        semantic_extraction_result=extraction,
    )
    context_b = _sample_context(
        request=request_b,
        run_id="run-request-b",
        semantic_extraction_result=extraction,
    )
    estimator_a = build_estimator_with_registered_run(context_a)
    estimator_b = build_estimator_with_registered_run(context_b)

    estimate_a = estimator_a.execute(context_a).internal_feature_estimate
    estimate_b = estimator_b.execute(context_b).internal_feature_estimate

    assert estimate_a is not None
    assert estimate_b is not None
    _assert_feature_vector(estimate_a.internal_feature_delta, estimate_b.internal_feature_delta)
    assert estimate_a.preferred_delta == estimate_b.preferred_delta


# §14 No.16 DB 非永続化
def test_execute_does_not_persist_user_feature_or_mutate_rule_repository() -> None:
    extraction = _extraction_with_concepts(
        ExtractedSemanticConcept(
            concept_code="formal_refined",
            confidence=0.85,
            input_intent="prefer",
            extraction_method="rule",
            source_type="preferred_condition",
        ),
    )
    context = _sample_context(
        run_id="run-no-db",
        semantic_extraction_result=extraction,
    )
    rules = build_default_concept_feature_rule_repository()
    rules_snapshot = dict(rules.rules_by_concept)
    estimator = build_estimator_with_registered_run(context, concept_feature_rules=rules)
    run_versions_before = dict(estimator.run_validation.run_versions)
    estimator_field_names = {field.name for field in fields(estimator)}

    updated = estimator.execute(context)

    assert updated.internal_feature_estimate is not None
    assert estimator.run_validation.run_versions == run_versions_before
    assert rules.rules_by_concept == rules_snapshot
    assert "user_feature" not in estimator_field_names


# §14 No.18 ログ
def test_execute_emits_structured_log_with_trace_id_without_secrets() -> None:
    context = _sample_context(
        run_id="run-log",
        semantic_extraction_result=_empty_extraction_result(),
    )
    logger = ScaffoldRecoLogger()
    estimator = build_estimator_with_registered_run(context, logger=logger)

    estimator.execute(context)

    completion_logs = [
        record
        for record in logger.records
        if record.event == "internal_feature_estimation_completed"
    ]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == context.trace_id
    serialized = json.dumps(log_record.attributes, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert "password" not in serialized
    assert "token" not in serialized


# §14 No.20 出力受け渡し
def test_execute_attaches_internal_feature_estimate_to_execution_context() -> None:
    context = _sample_context(
        run_id="run-handoff",
        semantic_extraction_result=_empty_extraction_result(),
    )
    estimator = build_estimator_with_registered_run(context)

    updated = estimator.execute(context)

    estimate = updated.internal_feature_estimate
    assert isinstance(estimate, InternalFeatureEstimate)
    assert estimate.semantic_config_version_id == DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    assert set(estimate.internal_feature_delta) == set(MVP_FEATURE_CODES)
    assert set(estimate.preferred_delta) == set(MVP_FEATURE_CODES)
    assert set(estimate.avoid_delta) == set(MVP_FEATURE_CODES)
    assert set(estimate.free_text_delta) == set(MVP_FEATURE_CODES)
