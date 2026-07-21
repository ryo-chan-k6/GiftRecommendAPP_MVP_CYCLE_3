"""Test bootstrap and shared fixtures for MOD-RECO-016 smoke tests."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

from reco.application.config_version_resolver import (
    DEFAULT_MATCHING_CONFIG_ID,
    DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
)
from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)
from reco.application.user_context_builder.models import (
    CompletedUserMeaning,
    UserContext,
    PreferredContext,
    NonPreferredContext,
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
    "reco.application.feature_matcher",
    "src/reco/application/feature-matcher",
)
_load_package(
    "reco.application.meaning_match_aggregator",
    "src/reco/application/meaning-match-aggregator",
)
_load_package(
    "reco.application.context_scorer",
    "src/reco/application/context-scorer",
)

from reco.application.context_scorer import (  # noqa: E402
    ContextScorer,
    ContextScoreResult,
    ContextScorerRunMetrics,
)
from reco.application.meaning_match_aggregator.models import (  # noqa: E402
    MeaningMatchEntry,
    MeaningMatchResult,
)

DEFAULT_RUN_ID = "run-context-scorer-1"


def _default_config_versions() -> dict[str, str]:
    return {
        "semantic_config_version_id": DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        "matching_config_id": DEFAULT_MATCHING_CONFIG_ID,
        "context_score_formula": "lambda_ctx_weighted",
    }


def _meaning_match_entry(
    *,
    item_id: str,
    social_match: float,
    symbolic_match: float,
    matching_config_id: str = DEFAULT_MATCHING_CONFIG_ID,
) -> MeaningMatchEntry:
    return MeaningMatchEntry(
        item_id=item_id,
        social_match=social_match,
        symbolic_match=symbolic_match,
        aggregation_method="weighted_average",
        calculated_at=datetime.now(UTC),
        matching_config_id=matching_config_id,
    )


def _sample_meaning_match_result(
    *,
    entries: tuple[MeaningMatchEntry, ...] | None = None,
) -> MeaningMatchResult:
    resolved_entries = entries or (
        _meaning_match_entry(
            item_id="item-001",
            social_match=0.82,
            symbolic_match=0.70,
        ),
    )
    return MeaningMatchResult(
        entries=resolved_entries,
        total_aggregated=len(resolved_entries),
    )


def _completed_user_meaning(*, lambda_ctx: float = 0.40) -> CompletedUserMeaning:
    return CompletedUserMeaning(
        recommendation_run_id=DEFAULT_RUN_ID,
        user_social=0.5,
        user_symbolic=0.5,
        lambda_ctx=lambda_ctx,
        feature_normalization_version_id="norm-v1",
        user_meaning_id="user-meaning-1",
        generated_at=datetime.now(UTC),
    )


def _sample_context(
    *,
    run_id: str = DEFAULT_RUN_ID,
    meaning_match_result: MeaningMatchResult | None = None,
    config_versions: dict[str, str] | None = None,
    lambda_ctx: float = 0.40,
    trace_id: str = "trace-context-scorer",
) -> ExecutionContext:
    request = RecommendationRequest(
        request_id="req-context-scorer-1",
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
            semantic_config_version=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
            model_version="embedding-v1",
        ),
        user_meaning=_completed_user_meaning(lambda_ctx=lambda_ctx),
        user_context=UserContext(
            preferred_context=PreferredContext(
                context_query="query",
                embedding_query_text="embedding",
            ),
            non_preferred_context=NonPreferredContext(),
            lambda_ctx=lambda_ctx,
        ),
    )
    context.meaning_match_result = meaning_match_result or _sample_meaning_match_result()  # type: ignore[attr-defined]
    return context


def build_scorer(
    *,
    logger: ScaffoldRecoLogger | None = None,
) -> ContextScorer:
    if logger is None:
        return ContextScorer()
    return ContextScorer(logger=logger)


def run_scoring_from_context(
    context: ExecutionContext,
) -> tuple[ContextScoreResult, ContextScorerRunMetrics]:
    scorer = build_scorer()
    return scorer.score_context(context)
