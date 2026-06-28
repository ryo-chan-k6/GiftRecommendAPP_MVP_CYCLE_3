"""MOD-RECO-006 Internal Condition Feature Estimator smoke tests."""

from __future__ import annotations

import json

import pytest

from conftest import build_estimator_with_registered_run, _sample_context
from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
from reco.application.internal_condition_feature_estimator import (
    ESTIMATION_METHOD_RULE,
    InternalFeatureEstimate,
    InternalFeatureEstimateError,
    SURFACE_ERROR_CODE,
    merge_internal_feature_delta,
    zero_feature_vector,
)
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES
from reco.domain.semantic_extraction import ExtractedSemanticConcept, SemanticExtractionResult
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
) -> SemanticExtractionResult:
    return SemanticExtractionResult(
        concepts=concepts,
        hard_filter_candidates=(),
        user_semantic_id="us-1",
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
    )


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


def test_merge_internal_feature_delta_matches_spec_formula() -> None:
    axes = MVP_FEATURE_CODES
    preferred = {axis: 0.20 for axis in axes}
    avoid = {axis: -0.10 for axis in axes}
    free_text = {axis: 0.05 for axis in axes}

    merged = merge_internal_feature_delta(preferred, avoid, free_text)

    assert merged["formality"] == pytest.approx(0.20 - 0.10 + 0.05)


def test_execute_raises_when_semantic_extraction_result_is_missing() -> None:
    context = _sample_context(run_id="run-no-semantic")
    estimator = build_estimator_with_registered_run(context)

    with pytest.raises(InternalFeatureEstimateError) as exc_info:
        estimator.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


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
