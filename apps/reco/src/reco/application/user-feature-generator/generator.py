"""MOD-RECO-007 User Feature Generator implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import TYPE_CHECKING

from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import MODULE_ID, PHASE_NAME, SOURCE_TYPE_AGGREGATED
from .errors import UserFeatureGenerationError
from .models import UserFeature, UserFeatureInsertRow
from .ports import (
    NormalizationRuleRepositoryPort,
    RunValidationPort,
    UserFeatureRepositoryPort,
)
from .rule_engine import merge_user_feature_raw, normalize_user_features

if TYPE_CHECKING:
    from reco.application.external_condition_feature_estimator.models import (
        ExternalFeatureEstimate,
    )
    from reco.application.internal_condition_feature_estimator.models import (
        InternalFeatureEstimate,
    )
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


@dataclass
class UserFeatureGenerator:
    """PipelineModulePort implementation for User Feature merge, normalize, persist."""

    normalization_rules: NormalizationRuleRepositoryPort
    user_features: UserFeatureRepositoryPort
    run_validation: RunValidationPort
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        user_feature = self.generate(context)
        _attach_user_feature(context, user_feature)
        context.completed_modules.append(self.module_id)
        return context

    def generate(self, context: ExecutionContext) -> UserFeature:
        started = perf_counter()
        run_id, semantic_version_id, external_estimate, internal_estimate = (
            self._validate_context(context)
        )

        if not self.user_features.has_user_semantic(run_id):
            raise UserFeatureGenerationError(
                f"user_semantic not found for run: {run_id}",
            )

        user_feature_raw = merge_user_feature_raw(
            external_estimate.external_feature_raw,
            internal_estimate.internal_feature_delta,
        )

        binding = self.normalization_rules.get_active_normalization_binding(
            semantic_version_id,
        )
        if binding is None:
            raise UserFeatureGenerationError(
                f"active normalization_rule not found: {semantic_version_id}",
            )

        normalized_features, stats = normalize_user_features(
            user_feature_raw,
            binding.parameters,
        )
        generated_at = datetime.now(UTC)
        user_feature = UserFeature(
            recommendation_run_id=run_id,
            features=normalized_features,
            user_feature_raw=user_feature_raw,
            feature_normalization_version_id=binding.feature_normalization_version_id,
            semantic_config_version_id=semantic_version_id,
            generated_at=generated_at,
        )

        insert_rows = tuple(
            UserFeatureInsertRow(
                recommendation_run_id=run_id,
                feature_code=feature_code,
                feature_value=feature_value,
                feature_normalization_version_id=binding.feature_normalization_version_id,
                source_type=SOURCE_TYPE_AGGREGATED,
                generated_at=generated_at,
            )
            for feature_code, feature_value in normalized_features.items()
        )
        try:
            self.user_features.insert_user_features(insert_rows)
        except Exception as exc:  # noqa: BLE001 — DB 回復不能を GRS-REC-005 へ集約
            raise UserFeatureGenerationError(
                f"user_feature insert failed for run: {run_id}",
            ) from exc

        duration_ms = int((perf_counter() - started) * 1_000)
        self._log_generation_summary(
            context,
            feature_normalization_version_id=binding.feature_normalization_version_id,
            duration_ms=duration_ms,
            normalized_features=normalized_features,
            raw_out_of_range_count=stats.raw_out_of_range_count,
            guard_clip_applied_count=stats.guard_clip_applied_count,
        )
        return user_feature

    def _validate_context(
        self,
        context: ExecutionContext,
    ) -> tuple[str, str, ExternalFeatureEstimate, InternalFeatureEstimate]:
        run_id = context.run_id
        if run_id is None:
            raise UserFeatureGenerationError("run_id is required on execution_context")

        semantic_version_id = context.config_versions.get("semantic_config_version_id")
        if not semantic_version_id:
            raise UserFeatureGenerationError(
                "semantic_config_version_id is required on execution_context.config_versions",
            )

        external_estimate = context.external_feature_estimate
        if external_estimate is None:
            raise UserFeatureGenerationError(
                "external_feature_estimate is required on execution_context",
            )

        internal_estimate = getattr(context, "internal_feature_estimate", None)
        if internal_estimate is None:
            raise UserFeatureGenerationError(
                "internal_feature_estimate is required on execution_context",
            )

        run_version_id = self.run_validation.get_semantic_config_version_id(run_id)
        if run_version_id is None:
            raise UserFeatureGenerationError(f"recommendation_run not found: {run_id}")
        if run_version_id != semantic_version_id:
            raise UserFeatureGenerationError(
                "semantic_config_version_id mismatch between run and execution_context",
            )

        return run_id, semantic_version_id, external_estimate, internal_estimate

    def _log_generation_summary(
        self,
        context: ExecutionContext,
        *,
        feature_normalization_version_id: str,
        duration_ms: int,
        normalized_features: dict[str, float],
        raw_out_of_range_count: int,
        guard_clip_applied_count: int,
    ) -> None:
        values = list(normalized_features.values())
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            "user_feature_generation_completed",
            feature_normalization_version_id=feature_normalization_version_id,
            duration_ms=duration_ms,
            normalized_min=min(values),
            normalized_max=max(values),
            raw_out_of_range_count=raw_out_of_range_count,
            guard_clip_applied_count=guard_clip_applied_count,
            module_id=self.module_id,
        )


def _attach_user_feature(context: ExecutionContext, user_feature: UserFeature) -> None:
    # execution_context への型付きフィールド追加は Wiring Task で行う。
    context.user_feature = user_feature  # type: ignore[attr-defined]


def build_default_user_feature_generator() -> UserFeatureGenerator:
    from .in_memory_repository import build_default_in_memory_repositories

    normalization_rules, user_features, run_validation = build_default_in_memory_repositories()
    return UserFeatureGenerator(
        normalization_rules=normalization_rules,
        user_features=user_features,
        run_validation=run_validation,
    )
