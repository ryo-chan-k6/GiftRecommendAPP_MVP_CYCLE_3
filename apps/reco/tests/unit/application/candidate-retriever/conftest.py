"""Test bootstrap and shared fixtures for MOD-RECO-012 smoke tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from reco.application.config_version_resolver import (
    DEFAULT_EMBEDDING_MODEL_VERSION_ID,
    DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
)
from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)
from reco.domain import (
    BudgetCondition,
    ExecutionCondition,
    ExecutionMode,
    NgCondition,
    OccasionCondition,
    PreferredCondition,
    RecommendationRequest,
    RecommendationRun,
    RelationshipCondition,
    RunStatus,
)
from reco.domain.semantic_extraction.models import (
    HardFilterCandidate,
    SemanticExtractionResult,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


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
    "reco.application.query_embedding_generator",
    "src/reco/application/query-embedding-generator",
)
_load_package(
    "reco.application.candidate_retriever",
    "src/reco/application/candidate-retriever",
)

from reco.application.candidate_retriever import (  # noqa: E402
    CandidateRetriever,
    InMemoryItemRecord,
    InMemoryItemRepository,
    PoolRepresentation,
)
from reco.application.query_embedding_generator.models import (  # noqa: E402
    PreferredEmbedding,
    QueryEmbedding,
)

DEFAULT_RUN_ID = "run-candidate-retriever-1"
EMBEDDING_DIMENSIONS = 4


def _sample_query_embedding(
    *,
    model_version_id: str = DEFAULT_EMBEDDING_MODEL_VERSION_ID,
) -> QueryEmbedding:
    return QueryEmbedding(
        preferred_embedding=PreferredEmbedding(
            vector=(1.0, 0.0, 0.0, 0.0),
            model_version_id=model_version_id,
            dimensions=EMBEDDING_DIMENSIONS,
            source_text_hash="hash-smoke",
        ),
    )


def _sample_semantic_extraction_result() -> SemanticExtractionResult:
    return SemanticExtractionResult(
        concepts=(),
        hard_filter_candidates=(
            HardFilterCandidate(
                filter_type="ng_category",
                filter_value="fashion",
                evidence_text="避けたい",
                confidence=0.8,
                source_type="semantic",
            ),
        ),
        user_semantic_id="user-semantic-1",
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
    )


def _sample_context(
    *,
    run_id: str = DEFAULT_RUN_ID,
    item_repository: InMemoryItemRepository | None = None,
    embedding_model_version_id: str = DEFAULT_EMBEDDING_MODEL_VERSION_ID,
) -> ExecutionContext:
    request = RecommendationRequest(
        request_id="req-candidate-retriever-1",
        relationship=RelationshipCondition(
            relationship_code="lover",
            relationship_label="恋人",
        ),
        occasion=OccasionCondition(
            occasion_code="birthday",
            occasion_label="誕生日",
        ),
        preferred_condition=PreferredCondition(preferred_text="実用的なギフト"),
        budget=BudgetCondition(budget_min=3000, budget_max=10000),
        ng_condition=NgCondition(ng_keywords=("カジュアル",)),
        execution=ExecutionCondition(mode=ExecutionMode.UI, candidate_limit=10),
    )
    context = ExecutionContext(
        recommendation_request=request,
        trace_id="trace-candidate-retriever",
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
        semantic_extraction_result=_sample_semantic_extraction_result(),
    )
    context.query_embedding = _sample_query_embedding(  # type: ignore[attr-defined]
        model_version_id=embedding_model_version_id,
    )
    return context


def build_retriever_with_repository(
    context: ExecutionContext,
    *,
    item_repository: InMemoryItemRepository | None = None,
    logger: ScaffoldRecoLogger | None = None,
) -> tuple[CandidateRetriever, InMemoryItemRepository]:
    repo = item_repository or InMemoryItemRepository(
        items=(
            InMemoryItemRecord(
                item_id="item-001",
                price=5000,
                is_active=True,
                active_status="active",
                keywords=("実用的",),
                categories=("gift",),
                embedding=(1.0, 0.0, 0.0, 0.0),
                model_version_id=context.config_versions["model_versions.embedding"],
            ),
            InMemoryItemRecord(
                item_id="item-002",
                price=8000,
                is_active=True,
                active_status="active",
                keywords=("カジュアル",),
                categories=("fashion",),
                embedding=(0.5, 0.5, 0.0, 0.0),
                model_version_id=context.config_versions["model_versions.embedding"],
            ),
            InMemoryItemRecord(
                item_id="item-003",
                price=12000,
                is_active=True,
                active_status="active",
                keywords=("高級",),
                categories=("gift",),
                embedding=(0.0, 0.0, 1.0, 0.0),
                model_version_id=context.config_versions["model_versions.embedding"],
            ),
        ),
    )
    retriever = CandidateRetriever(
        item_repository=repo,
        logger=logger or ScaffoldRecoLogger(),
    )
    return retriever, repo
