"""Test bootstrap and shared fixtures for MOD-RECO-021 unit tests."""

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
    "reco.application.meaning_match_aggregator",
    "src/reco/application/meaning-match-aggregator",
)
_load_package(
    "reco.application.popularity_scorer",
    "src/reco/application/popularity-scorer",
)
_load_package(
    "reco.application.risk_scorer",
    "src/reco/application/risk-scorer",
)
_load_package(
    "reco.application.final_ranker",
    "src/reco/application/final-ranker",
)
_load_package(
    "reco.application.recommendation_result_builder",
    "src/reco/application/recommendation-result-builder",
)

from reco.application.context_scorer.models import ContextScoreEntry, ContextScoreResult  # noqa: E402
from reco.application.final_ranker.models import RankedItemEntry, RankedItems  # noqa: E402
from reco.application.meaning_match_aggregator.models import (  # noqa: E402
    MeaningMatchEntry,
    MeaningMatchResult,
)
from reco.application.popularity_scorer.models import PopularityScoreEntry, PopularityScoreResult  # noqa: E402
from reco.application.recommendation_result_builder import (  # noqa: E402
    BuiltRecommendationResult,
    InMemoryRecommendationResultRepository,
    RecommendationResultBuilder,
    RecommendationResultBuilderRunMetrics,
    build_default_recommendation_result_builder,
)
from reco.application.risk_scorer.models import RiskPenaltyEntry, RiskPenaltyResult  # noqa: E402
from reco.domain.recommendation.result import ResultStatus  # noqa: E402

DEFAULT_RUN_ID = "run-result-builder-1"
DEFAULT_MATCHING_CONFIG_ID = "c1111111-1111-4111-8111-111111111102"


def _default_config_versions() -> dict[str, str]:
    return {
        "semantic_config_version_id": "a1111111-1111-4111-8111-111111111102",
        "model_version_id": "embedding-v1",
        "matching_config_id": DEFAULT_MATCHING_CONFIG_ID,
        "ranking_config_id": DEFAULT_RANKING_CONFIG_ID,
    }


def _ranked_item_entry(
    *,
    item_id: str = "item-001",
    rank: int = 1,
    final_score: float = 0.78,
) -> RankedItemEntry:
    return RankedItemEntry(
        item_id=item_id,
        rank=rank,
        final_score=final_score,
        pre_rank_score=0.80,
        diversity_penalty=0.05,
        score_breakdown={
            "diversity": {
                "penalty": 0.05,
                "max_similarity_to_selected": 0.42,
                "method": "mmr",
            },
        },
        is_displayed=True,
        ranking_config_id=DEFAULT_RANKING_CONFIG_ID,
        diversity_method="mmr",
        selected_at=datetime.now(UTC),
    )


def _sample_ranked_items(
    *,
    entries: tuple[RankedItemEntry, ...] | None = None,
) -> RankedItems:
    resolved_entries = entries or (_ranked_item_entry(),)
    return RankedItems(
        entries=resolved_entries,
        total_selected=len(resolved_entries),
        top_k_used=10,
        mmr_candidate_pool_size=len(resolved_entries),
        mmr_applied=False,
    )


def _context_score_entry(item_id: str = "item-001") -> ContextScoreEntry:
    return ContextScoreEntry(
        item_id=item_id,
        context_score=0.82,
        context_score_formula="lambda_ctx_v1",
        calculated_at=datetime.now(UTC),
        matching_config_id=DEFAULT_MATCHING_CONFIG_ID,
    )


def _meaning_match_entry(item_id: str = "item-001") -> MeaningMatchEntry:
    return MeaningMatchEntry(
        item_id=item_id,
        social_match=0.86,
        symbolic_match=0.76,
        aggregation_method="weighted_mean",
        calculated_at=datetime.now(UTC),
        matching_config_id=DEFAULT_MATCHING_CONFIG_ID,
    )


def _popularity_entry(item_id: str = "item-001") -> PopularityScoreEntry:
    return PopularityScoreEntry(
        item_id=item_id,
        popularity_score=0.64,
        popularity_formula="pop_v1",
        calculated_at=datetime.now(UTC),
        ranking_config_id=DEFAULT_RANKING_CONFIG_ID,
        signal_missing=False,
    )


def _risk_entry(item_id: str = "item-001") -> RiskPenaltyEntry:
    return RiskPenaltyEntry(
        item_id=item_id,
        risk_penalty=0.08,
        risk_formula="risk_v1",
        calculated_at=datetime.now(UTC),
        ranking_config_id=DEFAULT_RANKING_CONFIG_ID,
        signal_missing=False,
    )


def _sample_context(
    *,
    run_id: str = DEFAULT_RUN_ID,
    trace_id: str = "trace-result-builder",
    ranked_items: RankedItems | None = None,
    context_score_result: ContextScoreResult | None = None,
    meaning_match_result: MeaningMatchResult | None = None,
    popularity_score_result: PopularityScoreResult | None = None,
    risk_penalty_result: RiskPenaltyResult | None = None,
    config_versions: dict[str, str] | None = None,
    retrieval_candidate_count: int | None = 25,
) -> ExecutionContext:
    request = RecommendationRequest(
        request_id="req-result-builder-1",
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
        execution=ExecutionCondition(
            mode=ExecutionMode.UI,
            candidate_limit=10,
            top_k=10,
        ),
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
        retrieval_candidate_count=retrieval_candidate_count,
    )
    context.ranked_items = ranked_items or _sample_ranked_items()
    context.context_score_result = context_score_result or ContextScoreResult(
        entries=(_context_score_entry(),),
        lambda_ctx_applied=0.5,
        total_scored=1,
    )
    context.meaning_match_result = meaning_match_result or MeaningMatchResult(
        entries=(_meaning_match_entry(),),
        total_aggregated=1,
    )
    context.popularity_score_result = popularity_score_result or PopularityScoreResult(
        entries=(_popularity_entry(),),
        max_review_count_in_candidates=10,
        total_scored=1,
    )
    context.risk_penalty_result = risk_penalty_result or RiskPenaltyResult(
        entries=(_risk_entry(),),
        total_scored=1,
    )
    return context


def build_result_builder(
    *,
    repository: InMemoryRecommendationResultRepository | None = None,
    logger: ScaffoldRecoLogger | None = None,
) -> RecommendationResultBuilder:
    if repository is None and logger is None:
        return build_default_recommendation_result_builder()
    return RecommendationResultBuilder(
        result_repository=repository or InMemoryRecommendationResultRepository(),
        logger=logger or ScaffoldRecoLogger(),
    )


def run_build_from_context(
    context: ExecutionContext,
) -> tuple[BuiltRecommendationResult, RecommendationResultBuilderRunMetrics]:
    from reco.application.recommendation_result_builder import build_recommendation_result

    return build_recommendation_result(context)
