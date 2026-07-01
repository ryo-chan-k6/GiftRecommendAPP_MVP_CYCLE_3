"""MOD-RECO-009 User Context Builder implementation."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import TYPE_CHECKING

from reco.domain.gift_meaning.features import FEATURE_VALUE_MAX, FEATURE_VALUE_MIN, MVP_FEATURE_CODES
from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import (
    EXPECTED_USER_FEATURE_ROW_COUNT,
    LAMBDA_CTX_FALLBACK,
    MODULE_ID,
    PHASE_NAME,
)
from .context_engine import assemble_user_context
from .errors import UserContextBuildError
from .lambda_ctx_engine import resolve_lambda_ctx
from .models import CompletedUserMeaning, UserContext, UserMeaningInsertRow


@dataclass(frozen=True)
class UserContextBuildResult:
    completed_user_meaning: CompletedUserMeaning
    user_context: UserContext
from .ports import (
    LambdaContextRuleRepositoryPort,
    RunValidationPort,
    UserFeatureReadPort,
    UserMeaningRepositoryPort,
)

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )
    from reco.application.user_feature_generator.models import UserFeature
    from reco.application.user_meaning_projector.models import UserMeaningProjection


@dataclass
class UserContextBuilder:
    """PipelineModulePort implementation for User Context generation."""

    lambda_ctx_rules: LambdaContextRuleRepositoryPort
    user_meaning_repo: UserMeaningRepositoryPort
    user_features: UserFeatureReadPort
    run_validation: RunValidationPort
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        result = self.build(context)
        _attach_outputs(context, result)
        context.completed_modules.append(self.module_id)
        return context

    def build(self, context: ExecutionContext) -> UserContextBuildResult:
        started = perf_counter()
        run_id, semantic_version_id, projection, user_feature, request = (
            self._validate_context(context)
        )
        self._validate_user_feature_db_consistency(run_id, user_feature)

        relationship = request.relationship
        occasion = request.occasion
        assert relationship is not None and occasion is not None

        lambda_ctx, used_fallback = resolve_lambda_ctx(
            semantic_config_version_id=semantic_version_id,
            relationship_code=relationship.relationship_code,
            occasion_code=occasion.occasion_code,
            rule_repository=self.lambda_ctx_rules,
        )

        extraction_result = context.semantic_extraction_result
        assert extraction_result is not None

        user_context = assemble_user_context(
            request=request,
            concepts=extraction_result.concepts,
            lambda_ctx=lambda_ctx,
        )

        generated_at = datetime.now(UTC)
        insert_row = UserMeaningInsertRow(
            recommendation_run_id=run_id,
            feature_normalization_version_id=projection.feature_normalization_version_id,
            user_social=projection.user_social,
            user_symbolic=projection.user_symbolic,
            lambda_ctx=lambda_ctx,
            generated_at=generated_at,
        )
        try:
            user_meaning_id = self.user_meaning_repo.insert_user_meaning(insert_row)
        except UserContextBuildError:
            raise
        except Exception as exc:  # noqa: BLE001 — INSERT 回復不能を GRS-REC-005 へ集約
            raise UserContextBuildError(
                f"user_meaning insert failed for run: {run_id}",
            ) from exc

        if used_fallback:
            self._record_lambda_ctx_fallback_warning(context, run_id=run_id)

        duration_ms = int((perf_counter() - started) * 1_000)
        self._log_build_summary(
            context,
            lambda_ctx=lambda_ctx,
            context_query_len=len(user_context.preferred_context.context_query),
            duration_ms=duration_ms,
            used_fallback=used_fallback,
        )

        completed = CompletedUserMeaning(
            recommendation_run_id=run_id,
            user_social=projection.user_social,
            user_symbolic=projection.user_symbolic,
            lambda_ctx=lambda_ctx,
            feature_normalization_version_id=projection.feature_normalization_version_id,
            user_meaning_id=user_meaning_id,
            generated_at=generated_at,
        )
        return UserContextBuildResult(
            completed_user_meaning=completed,
            user_context=user_context,
        )

    def _validate_context(
        self,
        context: ExecutionContext,
    ) -> tuple[str, str, UserMeaningProjection, UserFeature, object]:
        run_id = context.run_id
        if run_id is None:
            raise UserContextBuildError("run_id is required on execution_context")

        semantic_version_id = context.config_versions.get("semantic_config_version_id")
        if not semantic_version_id:
            raise UserContextBuildError(
                "semantic_config_version_id is required on execution_context.config_versions",
            )

        projection = context.user_meaning
        if projection is None:
            raise UserContextBuildError("user_meaning is required on execution_context")
        self._validate_projection(projection)

        user_feature = context.user_feature
        if user_feature is None:
            raise UserContextBuildError("user_feature is required on execution_context")

        if context.semantic_extraction_result is None:
            raise UserContextBuildError(
                "semantic_extraction_result is required on execution_context",
            )

        request = context.recommendation_request
        if request.relationship is None or request.occasion is None:
            raise UserContextBuildError(
                "relationship and occasion are required on recommendation_request",
            )

        run_version_id = self.run_validation.get_semantic_config_version_id(run_id)
        if run_version_id is None:
            raise UserContextBuildError(f"recommendation_run not found: {run_id}")
        if run_version_id != semantic_version_id:
            raise UserContextBuildError(
                "semantic_config_version_id mismatch between run and execution_context",
            )

        return run_id, semantic_version_id, projection, user_feature, request

    def _validate_projection(self, projection: UserMeaningProjection) -> None:
        if getattr(projection, "lambda_ctx", None) is not None:
            raise UserContextBuildError(
                "user_meaning.lambda_ctx must not be set before MOD-RECO-009",
            )

        for field_name in ("user_social", "user_symbolic"):
            value = float(getattr(projection, field_name))
            if math.isnan(value) or math.isinf(value):
                raise UserContextBuildError(
                    f"user_meaning.{field_name} is non-finite",
                )
            if value < FEATURE_VALUE_MIN or value > FEATURE_VALUE_MAX:
                raise UserContextBuildError(
                    f"user_meaning.{field_name} out of range: {value}",
                )

    def _validate_user_feature_db_consistency(
        self,
        run_id: str,
        user_feature: UserFeature,
    ) -> None:
        rows = self.user_features.get_user_features_for_run(run_id)
        if len(rows) != EXPECTED_USER_FEATURE_ROW_COUNT:
            raise UserContextBuildError(
                f"user_feature row count mismatch for run {run_id}: {len(rows)}",
            )

        version_ids: set[str] = set()
        db_values: dict[str, float] = {}
        for row in rows:
            if row.feature_code not in MVP_FEATURE_CODES:
                raise UserContextBuildError(
                    f"unexpected user_feature feature_code: {row.feature_code}",
                )
            version_ids.add(row.feature_normalization_version_id)
            db_values[row.feature_code] = row.feature_value

        if len(version_ids) != 1:
            raise UserContextBuildError(
                "user_feature feature_normalization_version_id mismatch across DB rows",
            )

        db_version_id = next(iter(version_ids))
        if db_version_id != user_feature.feature_normalization_version_id:
            raise UserContextBuildError(
                "feature_normalization_version_id mismatch between context and DB",
            )

        for axis in MVP_FEATURE_CODES:
            if axis not in db_values:
                raise UserContextBuildError(
                    f"user_feature DB row missing axis: {axis}",
                )
            context_value = user_feature.features.get(axis)
            if context_value is None:
                raise UserContextBuildError(
                    f"user_feature.features missing axis: {axis}",
                )
            if db_values[axis] != float(context_value):
                raise UserContextBuildError(
                    f"user_feature value mismatch for axis {axis} between context and DB",
                )

    def _record_lambda_ctx_fallback_warning(
        self,
        context: ExecutionContext,
        *,
        run_id: str,
    ) -> None:
        message = (
            f"lambda_ctx rule not found; using fallback {LAMBDA_CTX_FALLBACK} for run {run_id}"
        )
        context.error_log_events.append(
            {
                "module_id": self.module_id,
                "level": "warning",
                "message": message,
                "trace_id": context.trace_id,
            },
        )

    def _log_build_summary(
        self,
        context: ExecutionContext,
        *,
        lambda_ctx: float,
        context_query_len: int,
        duration_ms: int,
        used_fallback: bool,
    ) -> None:
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            "user_context_build_completed",
            lambda_ctx=lambda_ctx,
            context_query_len=context_query_len,
            duration_ms=duration_ms,
            lambda_ctx_fallback=used_fallback,
            module_id=self.module_id,
        )


def _attach_outputs(
    context: ExecutionContext,
    result: UserContextBuildResult,
) -> None:
    context.user_context = result.user_context
    context.user_meaning = result.completed_user_meaning


def build_default_user_context_builder() -> UserContextBuilder:
    lambda_ctx_rules, user_meaning_repo, user_features, run_validation = (
        build_default_in_memory_repositories()
    )
    return UserContextBuilder(
        lambda_ctx_rules=lambda_ctx_rules,
        user_meaning_repo=user_meaning_repo,
        user_features=user_features,
        run_validation=run_validation,
    )


def build_default_in_memory_repositories():
    from .in_memory_repository import build_default_in_memory_repositories as _build

    return _build()
