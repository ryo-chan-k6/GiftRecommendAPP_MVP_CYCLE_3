"""Test bootstrap and shared fixtures for MOD-RECO-004 unit tests."""

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
    NgCondition,
    NonPreferredCondition,
    OccasionCondition,
    PreferredCondition,
    RecommendationRequest,
    RelationshipCondition,
    RecommendationRun,
    RunStatus,
)


def _load_user_semantic_extractor_package() -> None:
    init_path = (
        Path(__file__).resolve().parents[4]
        / "src/reco/application/user-semantic-extractor/__init__.py"
    )
    spec = importlib.util.spec_from_file_location(
        "reco.application.user_semantic_extractor",
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load user semantic extractor package")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_load_user_semantic_extractor_package()

from reco.application.user_semantic_extractor import (  # noqa: E402
    InMemoryRunValidation,
    UserSemanticExtractor,
    build_scaffold_user_semantic_extractor,
)

DEFAULT_RUN_ID = "run-semantic-extractor-1"


@pytest.fixture
def sample_context() -> ExecutionContext:
    return _sample_context()


def _sample_context(
    *,
    request: RecommendationRequest | None = None,
    run_id: str = DEFAULT_RUN_ID,
) -> ExecutionContext:
    resolved_request = request or RecommendationRequest(
        request_id="req-semantic-1",
        relationship=RelationshipCondition(relationship_code="friend"),
        occasion=OccasionCondition(occasion_code="birthday"),
        preferred_condition=PreferredCondition(
            preferred_text="上品で落ち着いたもの",
        ),
    )
    return ExecutionContext(
        recommendation_request=resolved_request,
        trace_id="trace-semantic-extractor",
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


def build_extractor_with_registered_run(
    context: ExecutionContext,
    *,
    should_fail_insert: bool = False,
) -> UserSemanticExtractor:
    extractor = build_scaffold_user_semantic_extractor(
        should_fail_insert=should_fail_insert,
    )
    assert context.run_id is not None
    semantic_version_id = context.config_versions["semantic_config_version_id"]
    assert isinstance(extractor.run_validation, InMemoryRunValidation)
    extractor.run_validation.register_run(context.run_id, semantic_version_id)
    return extractor
