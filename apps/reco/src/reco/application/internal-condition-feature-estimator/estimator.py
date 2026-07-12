"""MOD-RECO-006 Internal Condition Feature Estimator implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import ESTIMATION_METHOD_RULE, INTERNAL_SOURCE_TYPES, MODULE_ID, PHASE_NAME
from .errors import InternalFeatureEstimateError
from .models import InternalFeatureEstimate
from .ports import ConceptFeatureRuleRepositoryPort, RunValidationPort
from .rule_engine import aggregate_concept_deltas, merge_internal_feature_delta

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )
    from reco.domain.recommendation.request import RecommendationRequest
    from reco.domain.semantic_extraction import SemanticExtractionResult


@dataclass
class InternalConditionFeatureEstimator:
    """PipelineModulePort implementation for internal condition feature estimation."""

    concept_feature_rules: ConceptFeatureRuleRepositoryPort
    run_validation: RunValidationPort
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        estimate = self.estimate(context)
        _attach_internal_feature_estimate(context, estimate)
        context.completed_modules.append(self.module_id)
        return context

    def estimate(self, context: ExecutionContext) -> InternalFeatureEstimate:
        run_id, semantic_version_id, extraction_result = self._validate_context(context)
        integration_weights = self.concept_feature_rules.get_integration_weights(
            semantic_version_id,
        )

        def lookup_rules(concept_code: str):
            try:
                return self.concept_feature_rules.get_concept_feature_rules(
                    concept_code,
                    semantic_version_id,
                )
            except Exception as exc:  # noqa: BLE001 — DB 回復不能を GRS-REC-005 へ集約
                raise InternalFeatureEstimateError(
                    f"concept_feature_rule lookup failed: {concept_code}",
                ) from exc

        preferred_delta, avoid_delta, free_text_delta, applied_concept_count = (
            aggregate_concept_deltas(
                extraction_result.concepts,
                lookup_rules=lookup_rules,
                integration_weights=integration_weights,
            )
        )
        internal_feature_delta = merge_internal_feature_delta(
            preferred_delta,
            avoid_delta,
            free_text_delta,
            weights=integration_weights,
        )

        preferred_count, avoid_count, free_text_count = _count_applied_by_source_type(
            extraction_result,
        )
        self._log_request_inconsistency_warning(context, extraction_result)
        self._log_estimation_summary(
            context,
            applied_concept_count=applied_concept_count,
            preferred_count=preferred_count,
            avoid_count=avoid_count,
            free_text_count=free_text_count,
        )

        return InternalFeatureEstimate(
            preferred_delta=preferred_delta,
            avoid_delta=avoid_delta,
            free_text_delta=free_text_delta,
            internal_feature_delta=internal_feature_delta,
            applied_concept_count=applied_concept_count,
            semantic_config_version_id=semantic_version_id,
            estimation_method=ESTIMATION_METHOD_RULE,
        )

    def _validate_context(
        self,
        context: ExecutionContext,
    ) -> tuple[str, str, SemanticExtractionResult]:
        run_id = context.run_id
        if run_id is None:
            raise InternalFeatureEstimateError("run_id is required on execution_context")

        semantic_version_id = context.config_versions.get("semantic_config_version_id")
        if not semantic_version_id:
            raise InternalFeatureEstimateError(
                "semantic_config_version_id is required on execution_context.config_versions",
            )

        extraction_result = context.semantic_extraction_result
        if extraction_result is None:
            raise InternalFeatureEstimateError(
                "semantic_extraction_result is required on execution_context",
            )

        run_version_id = self.run_validation.get_semantic_config_version_id(run_id)
        if run_version_id is None:
            raise InternalFeatureEstimateError(f"recommendation_run not found: {run_id}")
        if run_version_id != semantic_version_id:
            raise InternalFeatureEstimateError(
                "semantic_config_version_id mismatch between run and execution_context",
            )

        return run_id, semantic_version_id, extraction_result

    def _log_request_inconsistency_warning(
        self,
        context: ExecutionContext,
        extraction_result: SemanticExtractionResult,
    ) -> None:
        # §16.1 No.4: Request と concepts[] の不整合は警告ログのみ。
        request = context.recommendation_request
        if _request_has_internal_input(request) and not _has_internal_concepts(
            extraction_result,
        ):
            self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).warning(
                "internal_feature_request_concept_mismatch",
                module_id=self.module_id,
            )

    def _log_estimation_summary(
        self,
        context: ExecutionContext,
        *,
        applied_concept_count: int,
        preferred_count: int,
        avoid_count: int,
        free_text_count: int,
    ) -> None:
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            "internal_feature_estimation_completed",
            applied_concept_count=applied_concept_count,
            preferred_count=preferred_count,
            avoid_count=avoid_count,
            free_text_count=free_text_count,
            module_id=self.module_id,
        )


def _attach_internal_feature_estimate(
    context: ExecutionContext,
    estimate: InternalFeatureEstimate,
) -> None:
    context.internal_feature_estimate = estimate


def _count_applied_by_source_type(
    extraction_result: SemanticExtractionResult,
) -> tuple[int, int, int]:
    from .rule_engine import should_apply_concept

    preferred_count = 0
    avoid_count = 0
    free_text_count = 0
    for concept in extraction_result.concepts:
        if not should_apply_concept(concept):
            continue
        if concept.source_type == "preferred_condition":
            preferred_count += 1
        elif concept.source_type == "non_preferred_condition":
            avoid_count += 1
        elif concept.source_type == "free_text":
            free_text_count += 1
    return preferred_count, avoid_count, free_text_count


def _request_has_internal_input(request: RecommendationRequest) -> bool:
    if request.free_text and request.free_text.strip():
        return True
    preferred = request.preferred_condition
    if preferred is not None and (
        (preferred.preferred_text and preferred.preferred_text.strip())
        or preferred.preferred_keywords
    ):
        return True
    non_preferred = request.non_preferred_condition
    if non_preferred is not None and (
        (non_preferred.non_preferred_text and non_preferred.non_preferred_text.strip())
        or non_preferred.non_preferred_keywords
    ):
        return True
    return False


def _has_internal_concepts(extraction_result: SemanticExtractionResult) -> bool:
    return any(
        concept.source_type in INTERNAL_SOURCE_TYPES
        for concept in extraction_result.concepts
    )


def build_default_internal_condition_feature_estimator() -> InternalConditionFeatureEstimator:
    from .in_memory_repository import build_default_in_memory_repositories

    concept_feature_rules, run_validation = build_default_in_memory_repositories()
    return InternalConditionFeatureEstimator(
        concept_feature_rules=concept_feature_rules,
        run_validation=run_validation,
    )
