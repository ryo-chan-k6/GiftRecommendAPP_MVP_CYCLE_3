"""MOD-RECO-005 External Condition Feature Estimator implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import ESTIMATION_METHOD_RULE, MODULE_ID, PHASE_NAME
from .errors import ExternalFeatureEstimateError
from .models import ExternalFeatureEstimate
from .ports import FeatureRuleRepositoryPort, RunValidationPort
from .rule_engine import (
    ensure_complete_feature_vector,
    merge_external_feature_raw,
    zero_feature_vector,
)

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


@dataclass
class ExternalConditionFeatureEstimator:
    """PipelineModulePort implementation for external condition feature estimation."""

    feature_rules: FeatureRuleRepositoryPort
    run_validation: RunValidationPort
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        estimate = self.estimate(context)
        _attach_external_feature_estimate(context, estimate)
        context.completed_modules.append(self.module_id)
        return context

    def estimate(self, context: ExecutionContext) -> ExternalFeatureEstimate:
        run_id, semantic_version_id, relationship_code, occasion_code = self._validate_context(
            context,
        )

        relationship_raw = self.feature_rules.get_relationship_features(
            relationship_code,
            semantic_version_id,
        )
        if relationship_raw is None:
            raise ExternalFeatureEstimateError(
                f"relationship_rule not found: {relationship_code}",
            )
        relationship_feature = ensure_complete_feature_vector(
            relationship_raw,
            rule_kind="relationship",
            code=relationship_code,
        )

        occasion_raw = self.feature_rules.get_occasion_features(
            occasion_code,
            semantic_version_id,
        )
        if occasion_raw is None:
            raise ExternalFeatureEstimateError(
                f"occasion_rule not found: {occasion_code}",
            )
        occasion_feature = ensure_complete_feature_vector(
            occasion_raw,
            rule_kind="occasion",
            code=occasion_code,
        )

        pair_raw = self.feature_rules.get_pair_delta(
            relationship_code,
            occasion_code,
            semantic_version_id,
        )
        pair_rule_applied = pair_raw is not None
        if pair_rule_applied:
            pair_delta = ensure_complete_feature_vector(
                pair_raw,
                rule_kind="pair",
                code=f"{relationship_code}×{occasion_code}",
            )
        else:
            pair_delta = zero_feature_vector()

        weights = self.feature_rules.get_integration_weights(semantic_version_id)
        external_feature_raw = merge_external_feature_raw(
            relationship_feature,
            occasion_feature,
            pair_delta,
            weights=weights,
        )

        self._log_estimation_summary(
            context,
            relationship_code=relationship_code,
            occasion_code=occasion_code,
            pair_rule_applied=pair_rule_applied,
        )

        return ExternalFeatureEstimate(
            relationship_code=relationship_code,
            occasion_code=occasion_code,
            relationship_feature=relationship_feature,
            occasion_feature=occasion_feature,
            pair_delta=pair_delta,
            external_feature_raw=external_feature_raw,
            semantic_config_version_id=semantic_version_id,
            estimation_method=ESTIMATION_METHOD_RULE,
        )

    def _validate_context(
        self,
        context: ExecutionContext,
    ) -> tuple[str, str, str, str]:
        run_id = context.run_id
        if run_id is None:
            raise ExternalFeatureEstimateError("run_id is required on execution_context")

        semantic_version_id = context.config_versions.get("semantic_config_version_id")
        if not semantic_version_id:
            raise ExternalFeatureEstimateError(
                "semantic_config_version_id is required on execution_context.config_versions",
            )

        request = context.recommendation_request
        if request.relationship is None or request.occasion is None:
            raise ExternalFeatureEstimateError(
                "relationship and occasion are required on recommendation_request",
            )

        relationship_code = request.relationship.relationship_code
        occasion_code = request.occasion.occasion_code
        if not relationship_code or not occasion_code:
            raise ExternalFeatureEstimateError(
                "relationship_code and occasion_code are required",
            )

        run_version_id = self.run_validation.get_semantic_config_version_id(run_id)
        if run_version_id is None:
            raise ExternalFeatureEstimateError(f"recommendation_run not found: {run_id}")
        if run_version_id != semantic_version_id:
            raise ExternalFeatureEstimateError(
                "semantic_config_version_id mismatch between run and execution_context",
            )

        # semantic_extraction_result は MVP では統合式に加算しない（MOD-RECO-005 §8.3）。
        return run_id, semantic_version_id, relationship_code, occasion_code

    def _log_estimation_summary(
        self,
        context: ExecutionContext,
        *,
        relationship_code: str,
        occasion_code: str,
        pair_rule_applied: bool,
    ) -> None:
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            "external_feature_estimation_completed",
            relationship_code=relationship_code,
            occasion_code=occasion_code,
            pair_rule_applied=pair_rule_applied,
            module_id=self.module_id,
        )


def _attach_external_feature_estimate(
    context: ExecutionContext,
    estimate: ExternalFeatureEstimate,
) -> None:
    context.external_feature_estimate = estimate


def build_default_external_condition_feature_estimator() -> ExternalConditionFeatureEstimator:
    from .in_memory_repository import build_default_in_memory_repositories

    feature_rules, run_validation = build_default_in_memory_repositories()
    return ExternalConditionFeatureEstimator(
        feature_rules=feature_rules,
        run_validation=run_validation,
    )
