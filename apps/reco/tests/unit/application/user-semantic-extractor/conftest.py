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
    InMemorySemanticCatalog,
    InMemoryUserSemanticRepository,
    UserSemanticExtractor,
    build_default_semantic_catalog,
)
from reco.application.user_semantic_extractor.models import (  # noqa: E402
    SemanticConceptRecord,
    SemanticRuleRecord,
)
from reco.infrastructure.external_ai.client import ScaffoldExternalAiClient
from reco.infrastructure.logger.logger import ScaffoldRecoLogger

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
    catalog: InMemorySemanticCatalog | None = None,
    logger: ScaffoldRecoLogger | None = None,
    llm_client: ScaffoldExternalAiClient | None = None,
    register_run: bool = True,
) -> UserSemanticExtractor:
    resolved_catalog = catalog or build_default_semantic_catalog()
    run_validation = InMemoryRunValidation()
    user_semantic_repo = InMemoryUserSemanticRepository(
        should_fail_on_insert=should_fail_insert,
    )
    extractor = UserSemanticExtractor(
        catalog=resolved_catalog,
        run_validation=run_validation,
        user_semantic_repository=user_semantic_repo,
        logger=logger or ScaffoldRecoLogger(),
        llm_client=llm_client or ScaffoldExternalAiClient(),
    )
    if register_run:
        assert context.run_id is not None
        semantic_version_id = context.config_versions["semantic_config_version_id"]
        run_validation.register_run(context.run_id, semantic_version_id)
    return extractor


def build_threshold_boundary_catalog() -> InMemorySemanticCatalog:
    """Catalog with rules at confidence 0.59 (excluded) and 0.60 (adopted)."""
    version_id = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    return InMemorySemanticCatalog(
        concepts=[
            SemanticConceptRecord("below_threshold", version_id),
            SemanticConceptRecord("at_threshold", version_id),
        ],
        rules=[
            SemanticRuleRecord(
                semantic_config_version_id=version_id,
                rule_type="keyword",
                match_value="低信頼",
                concept_code="below_threshold",
                confidence=0.59,
                source_types=("preferred_condition",),
                input_intent="prefer",
            ),
            SemanticRuleRecord(
                semantic_config_version_id=version_id,
                rule_type="keyword",
                match_value="高信頼",
                concept_code="at_threshold",
                confidence=0.60,
                source_types=("preferred_condition",),
                input_intent="prefer",
            ),
        ],
    )


def build_below_threshold_only_catalog() -> InMemorySemanticCatalog:
    version_id = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    return InMemorySemanticCatalog(
        concepts=[SemanticConceptRecord("weak_concept", version_id)],
        rules=[
            SemanticRuleRecord(
                semantic_config_version_id=version_id,
                rule_type="phrase",
                match_value="微妙",
                concept_code="weak_concept",
                confidence=0.55,
                source_types=("preferred_condition",),
                input_intent="prefer",
            ),
        ],
    )


def build_dedupe_catalog() -> InMemorySemanticCatalog:
    version_id = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    return InMemorySemanticCatalog(
        concepts=[SemanticConceptRecord("formal_refined", version_id)],
        rules=[
            SemanticRuleRecord(
                semantic_config_version_id=version_id,
                rule_type="phrase",
                match_value="上品",
                concept_code="formal_refined",
                confidence=0.70,
                source_types=("preferred_condition",),
                input_intent="prefer",
            ),
            SemanticRuleRecord(
                semantic_config_version_id=version_id,
                rule_type="phrase",
                match_value="落ち着",
                concept_code="formal_refined",
                confidence=0.92,
                source_types=("preferred_condition",),
                input_intent="prefer",
            ),
        ],
    )
