"""Test bootstrap and shared fixtures for MOD-RECO-010 smoke tests."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

from reco.application.config_version_resolver import (
    DEFAULT_EMBEDDING_MODEL_VERSION_ID,
    DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
)
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
    "reco.application.user_context_builder",
    "src/reco/application/user-context-builder",
)
_load_package(
    "reco.application.query_embedding_generator",
    "src/reco/application/query-embedding-generator",
)

from reco.application.query_embedding_generator import (  # noqa: E402
    EMBEDDING_DIMENSIONS,
    InMemoryEmbeddingApiClient,
    InMemoryRunValidation,
    QueryEmbeddingGenerator,
)
from reco.application.user_context_builder.models import (  # noqa: E402
    NonPreferredContext,
    PreferredContext,
    UserContext,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger

DEFAULT_RUN_ID = "run-query-embedding-generator-1"


def _sample_user_context(
    *,
    embedding_query_text: str = "恋人への誕生日。実用的なギフト。",
    avoid_query_text: str | None = "避けたいカジュアルすぎるもの",
) -> UserContext:
    return UserContext(
        preferred_context=PreferredContext(
            context_query="恋人への誕生日。実用的なギフト。",
            embedding_query_text=embedding_query_text,
            preferred_query="実用的なギフト",
        ),
        non_preferred_context=NonPreferredContext(
            avoid_query_text=avoid_query_text,
        ),
        lambda_ctx=0.5,
    )


def _sample_context(
    *,
    run_id: str = DEFAULT_RUN_ID,
    user_context: UserContext | None = None,
    embedding_model_version_id: str = DEFAULT_EMBEDDING_MODEL_VERSION_ID,
) -> ExecutionContext:
    request = RecommendationRequest(
        request_id="req-query-embedding-generator-1",
        relationship=RelationshipCondition(
            relationship_code="lover",
            relationship_label="恋人",
        ),
        occasion=OccasionCondition(
            occasion_code="birthday",
            occasion_label="誕生日",
        ),
        preferred_condition=PreferredCondition(preferred_text="実用的なギフト"),
    )
    context = ExecutionContext(
        recommendation_request=request,
        trace_id="trace-query-embedding-generator",
        execution_mode=ExecutionMode.UI,
        config_versions={
            "semantic_config_version_id": DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
            "model_versions.embedding": embedding_model_version_id,
        },
        recommendation_run=RecommendationRun(
            run_id=run_id,
            request_id=request.request_id,
            status=RunStatus.RUNNING,
            semantic_config_version=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
            model_version=embedding_model_version_id,
        ),
    )
    context.user_context = user_context or _sample_user_context()  # type: ignore[attr-defined]
    return context


def build_generator_with_registered_run(
    context: ExecutionContext,
    *,
    logger: ScaffoldRecoLogger | None = None,
    embedding_client: InMemoryEmbeddingApiClient | None = None,
    register_run: bool = True,
) -> tuple[QueryEmbeddingGenerator, InMemoryEmbeddingApiClient, InMemoryRunValidation]:
    assert context.run_id is not None
    embedding_model_version_id = context.config_versions.get("model_versions.embedding")

    run_validation = InMemoryRunValidation()
    if register_run and embedding_model_version_id is not None:
        run_validation.register_run(context.run_id, embedding_model_version_id)

    client = embedding_client or InMemoryEmbeddingApiClient()
    generator = QueryEmbeddingGenerator(
        embedding_client=client,
        run_validation=run_validation,
        logger=logger or ScaffoldRecoLogger(),
    )
    return generator, client, run_validation
