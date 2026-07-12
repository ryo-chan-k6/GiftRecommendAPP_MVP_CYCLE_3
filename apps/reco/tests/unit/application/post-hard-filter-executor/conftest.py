"""Test bootstrap and shared fixtures for MOD-RECO-013 unit tests."""

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
    ExtractedSemanticConcept,
    HardFilterCandidate,
    SemanticExtractionResult,
)
from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger


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
    "reco.application.candidate_retriever",
    "src/reco/application/candidate-retriever",
)
_load_package(
    "reco.application.post_hard_filter_executor",
    "src/reco/application/post-hard-filter-executor",
)

from reco.application.candidate_retriever.models import (  # noqa: E402
    RetrievalCandidate,
    RetrievalCandidateItem,
)
from reco.application.post_hard_filter_executor import (  # noqa: E402
    InMemoryItemRecord,
    InMemoryItemRepository,
    ItemSemanticConcept,
    PostHardFilterExecutor,
)

DEFAULT_RUN_ID = "run-post-hard-filter-1"


def _sample_semantic_extraction_result(
    *,
    concepts: tuple[ExtractedSemanticConcept, ...] = (),
    hard_filter_candidates: tuple[HardFilterCandidate, ...] | None = None,
) -> SemanticExtractionResult:
    return SemanticExtractionResult(
        concepts=concepts,
        hard_filter_candidates=(
            hard_filter_candidates
            if hard_filter_candidates is not None
            else (
                HardFilterCandidate(
                    filter_type="ng_category",
                    filter_value="fashion",
                    evidence_text="避けたい",
                    confidence=0.8,
                    source_type="semantic",
                ),
            )
        ),
        user_semantic_id="user-semantic-1",
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
    )


def build_item_record(
    *,
    item_id: str,
    name: str = "テスト商品",
    price: int = 5000,
    is_active: bool = True,
    active_status: str = "active",
    has_image: bool = True,
    semantic_concepts: tuple[ItemSemanticConcept, ...] = (
        ItemSemanticConcept(concept_code="practical", confidence=0.9),
    ),
) -> InMemoryItemRecord:
    return InMemoryItemRecord(
        item_id=item_id,
        name=name,
        price=price,
        is_active=is_active,
        active_status=active_status,
        has_image=has_image,
        semantic_concepts=semantic_concepts,
    )


def _sample_context(
    *,
    run_id: str = DEFAULT_RUN_ID,
    retrieval_candidate: RetrievalCandidate | None = None,
    concepts: tuple[ExtractedSemanticConcept, ...] = (),
    hard_filter_candidates: tuple[HardFilterCandidate, ...] | None = None,
    ng_keywords: tuple[str, ...] = ("カジュアル",),
    ng_categories: tuple[str, ...] = (),
    trace_id: str = "trace-post-hard-filter",
) -> ExecutionContext:
    request = RecommendationRequest(
        request_id="req-post-hard-filter-1",
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
        ng_condition=NgCondition(
            ng_keywords=ng_keywords,
            ng_categories=ng_categories,
        ),
        execution=ExecutionCondition(mode=ExecutionMode.UI, candidate_limit=10),
    )
    context = ExecutionContext(
        recommendation_request=request,
        trace_id=trace_id,
        execution_mode=ExecutionMode.UI,
        config_versions={
            "semantic_config_version_id": DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
            "model_versions.embedding": DEFAULT_EMBEDDING_MODEL_VERSION_ID,
        },
        recommendation_run=RecommendationRun(
            run_id=run_id,
            request_id=request.request_id,
            status=RunStatus.RUNNING,
            semantic_config_version=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
            model_version=DEFAULT_EMBEDDING_MODEL_VERSION_ID,
        ),
        semantic_extraction_result=_sample_semantic_extraction_result(
            concepts=concepts,
            hard_filter_candidates=hard_filter_candidates,
        ),
    )
    context.retrieval_candidate = retrieval_candidate or RetrievalCandidate(  # type: ignore[attr-defined]
        candidates=(
            RetrievalCandidateItem(item_id="item-001", similarity_score=0.95),
            RetrievalCandidateItem(item_id="item-002", similarity_score=0.80),
        ),
        total_retrieved=2,
    )
    return context


def build_executor_with_repository(
    context: ExecutionContext,
    *,
    item_repository: InMemoryItemRepository | None = None,
    logger: RecoLogger | None = None,
) -> tuple[PostHardFilterExecutor, InMemoryItemRepository]:
    repo = item_repository or InMemoryItemRepository(
        items={
            "item-001": InMemoryItemRecord(
                item_id="item-001",
                name="実用的ギフト",
                price=5000,
                is_active=True,
                active_status="active",
                semantic_concepts=(
                    ItemSemanticConcept(concept_code="practical", confidence=0.9),
                ),
            ),
            "item-002": InMemoryItemRecord(
                item_id="item-002",
                name="カジュアル雑貨",
                price=8000,
                is_active=True,
                active_status="active",
                semantic_concepts=(
                    ItemSemanticConcept(concept_code="casual", confidence=0.85),
                ),
            ),
        },
    )
    executor = PostHardFilterExecutor(
        item_repository=repo,
        logger=logger or ScaffoldRecoLogger(),
    )
    return executor, repo
