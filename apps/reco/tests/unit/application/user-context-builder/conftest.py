"""Test bootstrap and shared fixtures for MOD-RECO-009 smoke tests."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)
from reco.domain import (
    ExecutionMode,
    OccasionCondition,
    PreferredCondition,
    RecommendationRequest,
    RecommendationRun,
    RelationshipCondition,
    RunStatus,
)
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES
from reco.domain.semantic_extraction import ExtractedSemanticConcept, SemanticExtractionResult


def _load_package(import_root: str, relative_path: str) -> None:
    init_path = Path(__file__).resolve().parents[4] / relative_path / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        import_root,
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load package: {import_root}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_load_package(
    "reco.application.user_feature_generator",
    "src/reco/application/user-feature-generator",
)
_load_package(
    "reco.application.user_meaning_projector",
    "src/reco/application/user-meaning-projector",
)
_load_package(
    "reco.application.user_context_builder",
    "src/reco/application/user-context-builder",
)

from reco.application.user_feature_generator.models import UserFeature  # noqa: E402
from reco.application.user_context_builder import (  # noqa: E402
    InMemoryLambdaContextRuleRepository,
    InMemoryRunValidation,
    InMemoryUserFeatureReadRepository,
    InMemoryUserMeaningRepository,
    UserContextBuilder,
    UserFeatureRow,
)
from reco.application.user_meaning_projector.models import UserMeaningProjection  # noqa: E402
from reco.infrastructure.logger.logger import ScaffoldRecoLogger

DEFAULT_RUN_ID = "run-user-context-builder-1"
DEFAULT_FEATURE_NORMALIZATION_VERSION_ID = "fnv-mvp-sigmoid-default"


def _uniform_vector(value: float) -> dict[str, float]:
    return {code: value for code in MVP_FEATURE_CODES}


def _sample_user_feature(
    *,
    run_id: str = DEFAULT_RUN_ID,
    features: dict[str, float] | None = None,
    feature_normalization_version_id: str = DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
) -> UserFeature:
    generated_at = datetime.now(UTC)
    vector = features or _uniform_vector(0.5)
    return UserFeature(
        recommendation_run_id=run_id,
        features=vector,
        user_feature_raw=vector,
        feature_normalization_version_id=feature_normalization_version_id,
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        generated_at=generated_at,
    )


def _sample_user_meaning_projection(
    *,
    run_id: str = DEFAULT_RUN_ID,
    user_social: float = 0.5,
    user_symbolic: float = 0.5,
    feature_normalization_version_id: str = DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
) -> UserMeaningProjection:
    return UserMeaningProjection(
        recommendation_run_id=run_id,
        user_social=user_social,
        user_symbolic=user_symbolic,
        feature_normalization_version_id=feature_normalization_version_id,
        projected_at=datetime.now(UTC),
    )


def _sample_semantic_extraction_result() -> SemanticExtractionResult:
    return SemanticExtractionResult(
        concepts=(
            ExtractedSemanticConcept(
                concept_code="gift_practical",
                confidence=0.9,
                input_intent="preferred",
                extraction_method="rule",
                source_type="preferred_text",
            ),
        ),
        hard_filter_candidates=(),
        user_semantic_id="us-1",
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
    )


def _sample_context(
    *,
    run_id: str = DEFAULT_RUN_ID,
    user_feature: UserFeature | None = None,
    user_meaning: UserMeaningProjection | None = None,
    request: RecommendationRequest | None = None,
) -> ExecutionContext:
    request = request or RecommendationRequest(
        request_id="req-user-context-builder-1",
        relationship=RelationshipCondition(
            relationship_code="lover",
            relationship_label="恋人",
        ),
        occasion=OccasionCondition(
            occasion_code="birthday",
            occasion_label="誕生日",
        ),
        preferred_condition=PreferredCondition(preferred_text="実用的なギフト"),
        free_text="サプライズ希望",
    )
    context = ExecutionContext(
        recommendation_request=request,
        trace_id="trace-user-context-builder",
        execution_mode=ExecutionMode.UI,
        config_versions={
            "semantic_config_version_id": DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
            "model_version_id": "mv-1",
            "ranking_config_id": "rc-1",
        },
        recommendation_run=RecommendationRun(
            run_id=run_id,
            request_id=request.request_id,
            status=RunStatus.RUNNING,
            semantic_config_version=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
            model_version="mv-1",
        ),
        semantic_extraction_result=_sample_semantic_extraction_result(),
    )
    context.user_feature = user_feature or _sample_user_feature(run_id=run_id)  # type: ignore[attr-defined]
    context.user_meaning = user_meaning or _sample_user_meaning_projection(run_id=run_id)  # type: ignore[attr-defined]
    return context


def _user_feature_rows_from_vector(
    features: dict[str, float],
    *,
    feature_normalization_version_id: str = DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
) -> tuple[UserFeatureRow, ...]:
    return tuple(
        UserFeatureRow(
            feature_code=axis,
            feature_value=features[axis],
            feature_normalization_version_id=feature_normalization_version_id,
        )
        for axis in MVP_FEATURE_CODES
    )


def build_builder_with_registered_run(
    context: ExecutionContext,
    *,
    logger: ScaffoldRecoLogger | None = None,
    register_run: bool = True,
    user_feature_rows: tuple[UserFeatureRow, ...] | None = None,
    lambda_ctx_rules: InMemoryLambdaContextRuleRepository | None = None,
) -> tuple[
    UserContextBuilder,
    InMemoryUserMeaningRepository,
    InMemoryUserFeatureReadRepository,
    InMemoryRunValidation,
]:
    assert context.run_id is not None
    user_feature = context.user_feature  # type: ignore[attr-defined]
    semantic_version_id = context.config_versions["semantic_config_version_id"]

    run_validation = InMemoryRunValidation()
    if register_run:
        run_validation.register_run(context.run_id, semantic_version_id)

    rows = user_feature_rows or _user_feature_rows_from_vector(
        user_feature.features,
        feature_normalization_version_id=user_feature.feature_normalization_version_id,
    )
    user_features = InMemoryUserFeatureReadRepository()
    user_features.register_user_features(context.run_id, rows)

    rules = lambda_ctx_rules or InMemoryLambdaContextRuleRepository()
    user_meaning_repo = InMemoryUserMeaningRepository()

    builder = UserContextBuilder(
        lambda_ctx_rules=rules,
        user_meaning_repo=user_meaning_repo,
        user_features=user_features,
        run_validation=run_validation,
        logger=logger or ScaffoldRecoLogger(),
    )
    return builder, user_meaning_repo, user_features, run_validation
