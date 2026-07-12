"""MOD-RECO-014 Feature Matcher implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import MODULE_ID, PHASE_NAME
from .errors import FeatureMatcherError
from .match_engine import run_feature_matching
from .models import FeatureMatchResult, FeatureMatcherRunMetrics
from .ports import FeatureNormalizationPort, ItemFeatureRepositoryPort

if TYPE_CHECKING:
    from reco.application.internal_condition_feature_estimator.models import (
        InternalFeatureEstimate,
    )
    from reco.application.post_hard_filter_executor.models import (
        ValidatedRetrievalCandidate,
    )
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )
    from reco.application.user_feature_generator.models import UserFeature


@dataclass
class FeatureMatcher:
    """PipelineModulePort implementation for Feature Matcher."""

    item_feature_repository: ItemFeatureRepositoryPort
    normalization: FeatureNormalizationPort
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        result, metrics = self.match_features(context)
        _attach_outputs(context, result, metrics)
        context.completed_modules.append(self.module_id)
        return context

    def match_features(
        self,
        context: ExecutionContext,
    ) -> tuple[FeatureMatchResult, FeatureMatcherRunMetrics]:
        started = perf_counter()
        (
            user_feature,
            internal_estimate,
            validated_candidate,
            semantic_version_id,
            matching_config_id,
        ) = self._validate_context(context)

        try:
            result, metrics = run_feature_matching(
                user_feature=user_feature,
                internal_feature_estimate=internal_estimate,
                validated_retrieval_candidate=validated_candidate,
                semantic_config_version_id=semantic_version_id,
                matching_config_id=matching_config_id,
                item_feature_repository=self.item_feature_repository,
                normalization=self.normalization,
            )
        except FeatureMatcherError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise FeatureMatcherError(
                f"feature matching failed for run: {context.run_id}",
            ) from exc

        latency_ms = int((perf_counter() - started) * 1_000)
        metrics = FeatureMatcherRunMetrics(
            feature_matcher_candidate_count=metrics.feature_matcher_candidate_count,
            feature_matcher_excluded_count=metrics.feature_matcher_excluded_count,
            feature_matcher_latency_ms=latency_ms,
            feature_match_imputed_axis_count=metrics.feature_match_imputed_axis_count,
            feature_value_out_of_range_count=metrics.feature_value_out_of_range_count,
        )
        self._log_matching_completed(context, result, metrics)
        return result, metrics

    def _validate_context(
        self,
        context: ExecutionContext,
    ) -> tuple[
        UserFeature,
        InternalFeatureEstimate,
        ValidatedRetrievalCandidate,
        str,
        str,
    ]:
        if context.run_id is None:
            raise FeatureMatcherError("run_id is required on execution_context")

        semantic_version_id = context.config_versions.get("semantic_config_version_id")
        if not semantic_version_id:
            raise FeatureMatcherError(
                "semantic_config_version_id is required on execution_context.config_versions",
            )

        matching_config_id = context.config_versions.get("matching_config_id")
        if not matching_config_id:
            raise FeatureMatcherError(
                "matching_config_id is required on execution_context.config_versions",
            )

        user_feature = context.user_feature
        if user_feature is None:
            raise FeatureMatcherError("user_feature is required on execution_context")

        internal_estimate = context.internal_feature_estimate
        if internal_estimate is None:
            raise FeatureMatcherError(
                "internal_feature_estimate is required on execution_context",
            )

        validated_candidate = context.validated_retrieval_candidate
        if validated_candidate is None:
            raise FeatureMatcherError(
                "validated_retrieval_candidate is required on execution_context",
            )

        if user_feature.semantic_config_version_id != semantic_version_id:
            raise FeatureMatcherError(
                "semantic_config_version_id mismatch between user_feature and execution_context",
            )

        return (
            user_feature,
            internal_estimate,
            validated_candidate,
            str(semantic_version_id),
            str(matching_config_id),
        )

    def _log_matching_completed(
        self,
        context: ExecutionContext,
        result: FeatureMatchResult,
        metrics: FeatureMatcherRunMetrics,
    ) -> None:
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            PHASE_NAME,
            feature_matcher_candidate_count=metrics.feature_matcher_candidate_count,
            feature_matcher_excluded_count=metrics.feature_matcher_excluded_count,
            feature_matcher_latency_ms=metrics.feature_matcher_latency_ms,
            feature_match_imputed_axis_count=metrics.feature_match_imputed_axis_count,
            feature_value_out_of_range_count=metrics.feature_value_out_of_range_count,
            total_matched=result.total_matched,
            total_excluded=result.total_excluded,
            module_id=self.module_id,
        )


def _attach_outputs(
    context: ExecutionContext,
    result: FeatureMatchResult,
    metrics: FeatureMatcherRunMetrics,
) -> None:
    context.feature_match_result = result
    context.feature_matcher_candidate_count = metrics.feature_matcher_candidate_count
    context.feature_matcher_excluded_count = metrics.feature_matcher_excluded_count
    context.feature_matcher_latency_ms = metrics.feature_matcher_latency_ms
    context.feature_match_imputed_axis_count = metrics.feature_match_imputed_axis_count
    context.feature_value_out_of_range_count = metrics.feature_value_out_of_range_count


def build_default_feature_matcher() -> FeatureMatcher:
    from .in_memory_repository import build_default_in_memory_repositories

    item_features, normalization = build_default_in_memory_repositories()
    return FeatureMatcher(
        item_feature_repository=item_features,
        normalization=normalization,
    )
