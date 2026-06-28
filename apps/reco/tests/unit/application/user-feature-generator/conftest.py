"""Test bootstrap and shared fixtures for MOD-RECO-007 smoke tests."""

from __future__ import annotations

import importlib.util
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
    "reco.application.external_condition_feature_estimator",
    "src/reco/application/external-condition-feature-estimator",
)
_load_package(
    "reco.application.internal_condition_feature_estimator",
    "src/reco/application/internal-condition-feature-estimator",
)
_load_package(
    "reco.application.user_feature_generator",
    "src/reco/application/user-feature-generator",
)

from reco.application.external_condition_feature_estimator.models import (  # noqa: E402
    ExternalFeatureEstimate,
)
from reco.application.internal_condition_feature_estimator.models import (  # noqa: E402
    InternalFeatureEstimate,
)
from reco.application.user_feature_generator import (  # noqa: E402
    InMemoryNormalizationRuleRepository,
    InMemoryRunValidation,
    InMemoryUserFeatureRepository,
    UserFeatureGenerator,
    build_default_normalization_binding,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger

DEFAULT_RUN_ID = "run-user-feature-generator-smoke-1"


def _uniform_vector(value: float) -> dict[str, float]:
    return {code: value for code in MVP_FEATURE_CODES}


def _sample_external_estimate(
    *,
    external_feature_raw: dict[str, float] | None = None,
) -> ExternalFeatureEstimate:
    raw = external_feature_raw or _uniform_vector(0.5)
    return ExternalFeatureEstimate(
        relationship_code="lover",
        occasion_code="birthday",
        relationship_feature=_uniform_vector(0.4),
        occasion_feature=_uniform_vector(0.6),
        pair_delta=_uniform_vector(0.0),
        external_feature_raw=raw,
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        estimation_method="rule",
    )


def _sample_internal_estimate(
    *,
    internal_feature_delta: dict[str, float] | None = None,
) -> InternalFeatureEstimate:
    delta = internal_feature_delta or _uniform_vector(0.0)
    return InternalFeatureEstimate(
        preferred_delta=_uniform_vector(0.0),
        avoid_delta=_uniform_vector(0.0),
        free_text_delta=_uniform_vector(0.0),
        internal_feature_delta=delta,
        applied_concept_count=0,
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        estimation_method="rule",
    )


def _sample_context(
    *,
    run_id: str = DEFAULT_RUN_ID,
    external_feature_estimate: ExternalFeatureEstimate | None = None,
    internal_feature_estimate: InternalFeatureEstimate | None = None,
) -> ExecutionContext:
    request = RecommendationRequest(
        request_id="req-user-feature-smoke",
        relationship=RelationshipCondition(relationship_code="lover"),
        occasion=OccasionCondition(occasion_code="birthday"),
    )
    context = ExecutionContext(
        recommendation_request=request,
        trace_id="trace-user-feature-smoke",
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
        external_feature_estimate=external_feature_estimate or _sample_external_estimate(),
    )
    context.internal_feature_estimate = (  # type: ignore[attr-defined]
        internal_feature_estimate or _sample_internal_estimate()
    )
    return context


def build_generator_with_registered_run(
    context: ExecutionContext,
) -> tuple[UserFeatureGenerator, InMemoryUserFeatureRepository]:
    run_validation = InMemoryRunValidation()
    user_features = InMemoryUserFeatureRepository()
    assert context.run_id is not None
    semantic_version_id = context.config_versions["semantic_config_version_id"]
    run_validation.register_run(context.run_id, semantic_version_id)
    user_features.register_user_semantic(context.run_id)
    generator = UserFeatureGenerator(
        normalization_rules=InMemoryNormalizationRuleRepository(
            binding=build_default_normalization_binding(),
        ),
        user_features=user_features,
        run_validation=run_validation,
        logger=ScaffoldRecoLogger(),
    )
    return generator, user_features
