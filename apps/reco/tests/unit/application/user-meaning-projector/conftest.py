"""Test bootstrap and shared fixtures for MOD-RECO-008 smoke tests."""

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
    RecommendationRequest,
    RecommendationRun,
    RelationshipCondition,
    RunStatus,
)
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES


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

from reco.application.user_feature_generator.models import UserFeature  # noqa: E402
from reco.application.user_meaning_projector import (  # noqa: E402
    InMemoryMeaningProjectionConfigRepository,
    InMemoryRunValidation,
    InMemoryUserFeatureReadRepository,
    UserFeatureRow,
    UserMeaningProjector,
    build_default_projection_weights,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger

DEFAULT_RUN_ID = "run-user-meaning-projector-1"
DEFAULT_FEATURE_NORMALIZATION_VERSION_ID = "fnv-mvp-sigmoid-default"


def _uniform_vector(value: float) -> dict[str, float]:
    return {code: value for code in MVP_FEATURE_CODES}


def _sample_user_feature(*, run_id: str = DEFAULT_RUN_ID) -> UserFeature:
    generated_at = datetime.now(UTC)
    features = _uniform_vector(0.5)
    return UserFeature(
        recommendation_run_id=run_id,
        features=features,
        user_feature_raw=features,
        feature_normalization_version_id=DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        generated_at=generated_at,
    )


def _sample_context(
    *,
    run_id: str = DEFAULT_RUN_ID,
    user_feature: UserFeature | None = None,
) -> ExecutionContext:
    request = RecommendationRequest(
        request_id="req-user-meaning-projector-1",
        relationship=RelationshipCondition(relationship_code="lover"),
        occasion=OccasionCondition(occasion_code="birthday"),
    )
    context = ExecutionContext(
        recommendation_request=request,
        trace_id="trace-user-meaning-projector",
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
    )
    context.user_feature = user_feature or _sample_user_feature(run_id=run_id)  # type: ignore[attr-defined]
    return context


def build_projector_with_registered_run(
    context: ExecutionContext,
) -> UserMeaningProjector:
    assert context.run_id is not None
    user_feature = context.user_feature  # type: ignore[attr-defined]
    semantic_version_id = context.config_versions["semantic_config_version_id"]

    run_validation = InMemoryRunValidation()
    run_validation.register_run(context.run_id, semantic_version_id)

    user_feature_rows = tuple(
        UserFeatureRow(
            feature_code=axis,
            feature_value=user_feature.features[axis],
            feature_normalization_version_id=user_feature.feature_normalization_version_id,
        )
        for axis in MVP_FEATURE_CODES
    )
    user_features = InMemoryUserFeatureReadRepository()
    user_features.register_user_features(context.run_id, user_feature_rows)

    return UserMeaningProjector(
        projection_config=InMemoryMeaningProjectionConfigRepository(
            weights=build_default_projection_weights(),
        ),
        user_features=user_features,
        run_validation=run_validation,
        logger=ScaffoldRecoLogger(),
    )
