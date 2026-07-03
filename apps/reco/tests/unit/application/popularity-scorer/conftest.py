"""Test bootstrap and shared fixtures for MOD-RECO-017 smoke tests."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

from reco.application.config_version_resolver import DEFAULT_RANKING_CONFIG_ID
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
    "reco.application.context_scorer",
    "src/reco/application/context-scorer",
)
_load_package(
    "reco.application.popularity_scorer",
    "src/reco/application/popularity-scorer",
)

from reco.application.context_scorer.models import (  # noqa: E402
    ContextScoreEntry,
    ContextScoreResult,
)
from reco.application.popularity_scorer import (  # noqa: E402
    InMemoryItemReviewSummaryRepository,
    ItemReviewSummary,
    PopularityScorer,
    build_default_popularity_scorer,
)

DEFAULT_RUN_ID = "run-popularity-scorer-1"
DEFAULT_MATCHING_CONFIG_ID = "c1111111-1111-4111-8111-111111111102"


def _default_config_versions() -> dict[str, str]:
    return {
        "ranking_config_id": DEFAULT_RANKING_CONFIG_ID,
        "popularity_formula": "rating_review_count_weighted",
        "popularity_weights.rating": "0.60",
        "popularity_weights.review_count": "0.40",
    }


def _context_score_entry(
    *,
    item_id: str,
    context_score: float = 0.772,
    matching_config_id: str = DEFAULT_MATCHING_CONFIG_ID,
) -> ContextScoreEntry:
    return ContextScoreEntry(
        item_id=item_id,
        context_score=context_score,
        context_score_formula="lambda_ctx_weighted",
        calculated_at=datetime.now(UTC),
        matching_config_id=matching_config_id,
    )


def _sample_context_score_result(
    *,
    entries: tuple[ContextScoreEntry, ...] | None = None,
) -> ContextScoreResult:
    resolved_entries = entries or (_context_score_entry(item_id="item-001"),)
    return ContextScoreResult(
        entries=resolved_entries,
        lambda_ctx_applied=0.4,
        total_scored=len(resolved_entries),
    )


def _sample_context(
    *,
    run_id: str = DEFAULT_RUN_ID,
    context_score_result: ContextScoreResult | None = None,
    config_versions: dict[str, str] | None = None,
    trace_id: str = "trace-popularity-scorer",
) -> ExecutionContext:
    request = RecommendationRequest(
        request_id="req-popularity-scorer-1",
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
        ng_condition=NgCondition(ng_keywords=("カジュアル",), ng_categories=()),
        execution=ExecutionCondition(mode=ExecutionMode.UI, candidate_limit=10),
    )
    context = ExecutionContext(
        recommendation_request=request,
        trace_id=trace_id,
        execution_mode=ExecutionMode.UI,
        config_versions=config_versions or _default_config_versions(),
        recommendation_run=RecommendationRun(
            run_id=run_id,
            request_id=request.request_id,
            status=RunStatus.RUNNING,
            semantic_config_version="a1111111-1111-4111-8111-111111111102",
            model_version="embedding-v1",
        ),
    )
    context.context_score_result = context_score_result or _sample_context_score_result()  # type: ignore[attr-defined]
    return context


def build_review_repository(
    *,
    records: dict[str, ItemReviewSummary] | None = None,
    should_fail_on_fetch: bool = False,
) -> InMemoryItemReviewSummaryRepository:
    repo = InMemoryItemReviewSummaryRepository(
        records=dict(records or {}),
        should_fail_on_fetch=should_fail_on_fetch,
    )
    if records is None:
        repo.register_review_summary(
            "item-001",
            ItemReviewSummary(review_average=4.0, review_count=120),
        )
        repo.register_review_summary(
            "item-002",
            ItemReviewSummary(review_average=4.0, review_count=500),
        )
    return repo


def build_scorer(
    *,
    repository: InMemoryItemReviewSummaryRepository | None = None,
    logger: ScaffoldRecoLogger | None = None,
) -> PopularityScorer:
    repo = repository or build_review_repository()
    if logger is None:
        return build_default_popularity_scorer(repo)
    return PopularityScorer(review_summary_repository=repo, logger=logger)
