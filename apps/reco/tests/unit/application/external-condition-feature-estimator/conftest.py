"""Test bootstrap and shared fixtures for MOD-RECO-005 unit tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

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


def _load_external_condition_feature_estimator_package() -> None:
    init_path = (
        Path(__file__).resolve().parents[4]
        / "src/reco/application/external-condition-feature-estimator/__init__.py"
    )
    spec = importlib.util.spec_from_file_location(
        "reco.application.external_condition_feature_estimator",
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load external condition feature estimator package")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_load_external_condition_feature_estimator_package()

from reco.application.external_condition_feature_estimator import (  # noqa: E402
    ExternalConditionFeatureEstimator,
    InMemoryFeatureRuleRepository,
    InMemoryRunValidation,
    build_default_feature_rule_repository,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger

DEFAULT_RUN_ID = "run-external-feature-estimator-1"


@pytest.fixture
def sample_context() -> ExecutionContext:
    return _sample_context()


def _sample_context(
    *,
    request: RecommendationRequest | None = None,
    run_id: str = DEFAULT_RUN_ID,
) -> ExecutionContext:
    resolved_request = request or RecommendationRequest(
        request_id="req-external-1",
        relationship=RelationshipCondition(relationship_code="lover"),
        occasion=OccasionCondition(occasion_code="birthday"),
    )
    return ExecutionContext(
        recommendation_request=resolved_request,
        trace_id="trace-external-feature-estimator",
        execution_mode=ExecutionMode.UI,
        config_versions={
            "semantic_config_version_id": DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
            "model_version_id": "mv-1",
            "ranking_config_id": "rc-1",
        },
        recommendation_run=RecommendationRun(
            run_id=run_id,
            request_id=resolved_request.request_id,
            status=RunStatus.RUNNING,
            semantic_config_version=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
            model_version="mv-1",
        ),
    )


def build_estimator_with_registered_run(
    context: ExecutionContext,
    *,
    feature_rules: InMemoryFeatureRuleRepository | None = None,
    logger: ScaffoldRecoLogger | None = None,
    register_run: bool = True,
) -> ExternalConditionFeatureEstimator:
    resolved_rules = feature_rules or build_default_feature_rule_repository()
    run_validation = InMemoryRunValidation()
    estimator = ExternalConditionFeatureEstimator(
        feature_rules=resolved_rules,
        run_validation=run_validation,
        logger=logger or ScaffoldRecoLogger(),
    )
    if register_run:
        assert context.run_id is not None
        semantic_version_id = context.config_versions["semantic_config_version_id"]
        run_validation.register_run(context.run_id, semantic_version_id)
    return estimator
