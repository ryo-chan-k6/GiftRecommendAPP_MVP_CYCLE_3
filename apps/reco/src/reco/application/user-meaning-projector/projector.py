"""MOD-RECO-008 User Meaning Projector implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import TYPE_CHECKING

from reco.domain.gift_meaning.features import MVP_FEATURE_CODES
from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import (
    EXPECTED_USER_FEATURE_ROW_COUNT,
    MODULE_ID,
    PHASE_NAME,
)
from .errors import UserMeaningProjectionError
from .models import MeaningProjectionWeights, UserMeaningProjection
from .ports import (
    MeaningProjectionConfigRepositoryPort,
    RunValidationPort,
    UserFeatureReadPort,
)
from .projection_engine import project_user_meaning_coordinates

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )
    from reco.application.user_feature_generator.models import UserFeature


@dataclass
class UserMeaningProjector:
    """PipelineModulePort implementation for User Feature → Social / Symbolic projection."""

    projection_config: MeaningProjectionConfigRepositoryPort
    user_features: UserFeatureReadPort
    run_validation: RunValidationPort
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        projection = self.project(context)
        _attach_user_meaning(context, projection)
        context.completed_modules.append(self.module_id)
        return context

    def project(self, context: ExecutionContext) -> UserMeaningProjection:
        started = perf_counter()
        run_id, semantic_version_id, user_feature = self._validate_context(context)
        self._validate_user_feature_db_consistency(
            run_id,
            user_feature,
        )

        weights = self._resolve_projection_weights(semantic_version_id)
        user_social, user_symbolic, stats = project_user_meaning_coordinates(
            user_feature.features,
            weights,
        )
        projected_at = datetime.now(UTC)
        projection = UserMeaningProjection(
            recommendation_run_id=run_id,
            user_social=user_social,
            user_symbolic=user_symbolic,
            feature_normalization_version_id=user_feature.feature_normalization_version_id,
            projected_at=projected_at,
        )

        duration_ms = int((perf_counter() - started) * 1_000)
        self._log_projection_summary(
            context,
            user_social=user_social,
            user_symbolic=user_symbolic,
            duration_ms=duration_ms,
            guard_clip_applied_count=stats.guard_clip_applied_count,
        )
        return projection

    def _validate_context(
        self,
        context: ExecutionContext,
    ) -> tuple[str, str, UserFeature]:
        run_id = context.run_id
        if run_id is None:
            raise UserMeaningProjectionError("run_id is required on execution_context")

        semantic_version_id = context.config_versions.get("semantic_config_version_id")
        if not semantic_version_id:
            raise UserMeaningProjectionError(
                "semantic_config_version_id is required on execution_context.config_versions",
            )

        user_feature = context.user_feature
        if user_feature is None:
            raise UserMeaningProjectionError(
                "user_feature is required on execution_context",
            )

        run_version_id = self.run_validation.get_semantic_config_version_id(run_id)
        if run_version_id is None:
            raise UserMeaningProjectionError(f"recommendation_run not found: {run_id}")
        if run_version_id != semantic_version_id:
            raise UserMeaningProjectionError(
                "semantic_config_version_id mismatch between run and execution_context",
            )

        return run_id, semantic_version_id, user_feature

    def _validate_user_feature_db_consistency(
        self,
        run_id: str,
        user_feature: UserFeature,
    ) -> None:
        rows = self.user_features.get_user_features_for_run(run_id)
        if len(rows) != EXPECTED_USER_FEATURE_ROW_COUNT:
            raise UserMeaningProjectionError(
                f"user_feature row count mismatch for run {run_id}: {len(rows)}",
            )

        version_ids: set[str] = set()
        db_values: dict[str, float] = {}
        for row in rows:
            if row.feature_code not in MVP_FEATURE_CODES:
                raise UserMeaningProjectionError(
                    f"unexpected user_feature feature_code: {row.feature_code}",
                )
            version_ids.add(row.feature_normalization_version_id)
            db_values[row.feature_code] = row.feature_value

        if len(version_ids) != 1:
            raise UserMeaningProjectionError(
                "user_feature feature_normalization_version_id mismatch across DB rows",
            )

        db_version_id = next(iter(version_ids))
        if db_version_id != user_feature.feature_normalization_version_id:
            raise UserMeaningProjectionError(
                "feature_normalization_version_id mismatch between context and DB",
            )

        for axis in MVP_FEATURE_CODES:
            if axis not in db_values:
                raise UserMeaningProjectionError(
                    f"user_feature DB row missing axis: {axis}",
                )
            context_value = user_feature.features.get(axis)
            if context_value is None:
                raise UserMeaningProjectionError(
                    f"user_feature.features missing axis: {axis}",
                )
            if db_values[axis] != float(context_value):
                raise UserMeaningProjectionError(
                    f"user_feature value mismatch for axis {axis} between context and DB",
                )

    def _resolve_projection_weights(
        self,
        semantic_config_version_id: str,
    ) -> MeaningProjectionWeights:
        try:
            weights = self.projection_config.get_weights(semantic_config_version_id)
        except Exception as exc:  # noqa: BLE001 — 重み解決不能を GRS-REC-006 へ集約
            raise UserMeaningProjectionError(
                f"projection weight lookup failed: {semantic_config_version_id}",
            ) from exc

        if weights is None:
            raise UserMeaningProjectionError(
                f"projection weights not found: {semantic_config_version_id}",
            )
        return weights

    def _log_projection_summary(
        self,
        context: ExecutionContext,
        *,
        user_social: float,
        user_symbolic: float,
        duration_ms: int,
        guard_clip_applied_count: int,
    ) -> None:
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            "user_meaning_projection_completed",
            user_social=user_social,
            user_symbolic=user_symbolic,
            duration_ms=duration_ms,
            guard_clip_applied_count=guard_clip_applied_count,
            module_id=self.module_id,
        )


def _attach_user_meaning(
    context: ExecutionContext,
    projection: UserMeaningProjection,
) -> None:
    context.user_meaning = projection


def build_default_user_meaning_projector() -> UserMeaningProjector:
    from .in_memory_repository import build_default_in_memory_repositories

    projection_config, user_features, run_validation = build_default_in_memory_repositories()
    return UserMeaningProjector(
        projection_config=projection_config,
        user_features=user_features,
        run_validation=run_validation,
    )
