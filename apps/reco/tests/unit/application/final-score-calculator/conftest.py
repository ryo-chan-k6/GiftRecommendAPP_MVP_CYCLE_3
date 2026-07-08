"""Test bootstrap and shared fixtures for MOD-RECO-019 smoke tests."""

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
_load_package(
    "reco.application.risk_scorer",
    "src/reco/application/risk-scorer",
)
_load_package(
    "reco.application.final_score_calculator",
    "src/reco/application/final-score-calculator",
)

from reco.application.context_scorer.models import (  # noqa: E402
    ContextScoreEntry,
    ContextScoreResult,
)
from reco.application.final_score_calculator import (  # noqa: E402
    FinalScoreCalculator,
    FinalScoreCalculatorRunMetrics,
    FinalScoreResult,
    build_default_final_score_calculator,
)
from reco.application.popularity_scorer.models import (  # noqa: E402
    PopularityScoreEntry,
    PopularityScoreResult,
)
from reco.application.risk_scorer.models import (  # noqa: E402
    RiskPenaltyEntry,
    RiskPenaltyResult,
)

DEFAULT_RUN_ID = "run-final-score-calculator-1"
DEFAULT_MATCHING_CONFIG_ID = "c1111111-1111-4111-8111-111111111102"


def _default_config_versions() -> dict[str, str]:
    return {
        "ranking_config_id": DEFAULT_RANKING_CONFIG_ID,
        "final_score_formula": "linear_weighted_v1",
        "ranking_weights.context": "0.70",
        "ranking_weights.popularity": "0.20",
        "ranking_weights.risk": "0.10",
    }


def _context_score_entry(
    *,
    item_id: str,
    context_score: float | None = 0.84,
) -> ContextScoreEntry:
    return ContextScoreEntry(
        item_id=item_id,
        context_score=context_score,  # type: ignore[arg-type]
        context_score_formula="lambda_ctx_weighted",
        calculated_at=datetime.now(UTC),
        matching_config_id=DEFAULT_MATCHING_CONFIG_ID,
    )


def _popularity_score_entry(
    *,
    item_id: str,
    popularity_score: float | None = 0.72,
) -> PopularityScoreEntry:
    return PopularityScoreEntry(
        item_id=item_id,
        popularity_score=popularity_score,  # type: ignore[arg-type]
        popularity_formula="rating_review_count_weighted",
        calculated_at=datetime.now(UTC),
        ranking_config_id=DEFAULT_RANKING_CONFIG_ID,
        signal_missing=False,
    )


def _risk_penalty_entry(
    *,
    item_id: str,
    risk_penalty: float | None = 0.10,
) -> RiskPenaltyEntry:
    return RiskPenaltyEntry(
        item_id=item_id,
        risk_penalty=risk_penalty,  # type: ignore[arg-type]
        risk_formula="avoid_social_data_quality_weighted",
        calculated_at=datetime.now(UTC),
        ranking_config_id=DEFAULT_RANKING_CONFIG_ID,
        signal_missing=False,
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


def _sample_popularity_score_result(
    *,
    entries: tuple[PopularityScoreEntry, ...] | None = None,
) -> PopularityScoreResult:
    resolved_entries = entries or (_popularity_score_entry(item_id="item-001"),)
    return PopularityScoreResult(
        entries=resolved_entries,
        max_review_count_in_candidates=500,
        total_scored=len(resolved_entries),
    )


def _sample_risk_penalty_result(
    *,
    entries: tuple[RiskPenaltyEntry, ...] | None = None,
) -> RiskPenaltyResult:
    resolved_entries = entries or (_risk_penalty_entry(item_id="item-001"),)
    return RiskPenaltyResult(
        entries=resolved_entries,
        total_scored=len(resolved_entries),
    )


def _sample_context(
    *,
    run_id: str = DEFAULT_RUN_ID,
    context_score_result: ContextScoreResult | None = None,
    popularity_score_result: PopularityScoreResult | None = None,
    risk_penalty_result: RiskPenaltyResult | None = None,
    config_versions: dict[str, str] | None = None,
    trace_id: str = "trace-final-score-calculator",
) -> ExecutionContext:
    request = RecommendationRequest(
        request_id="req-final-score-calculator-1",
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
    context.context_score_result = (
        context_score_result or _sample_context_score_result()
    )
    context.popularity_score_result = (  # type: ignore[attr-defined]
        popularity_score_result or _sample_popularity_score_result()
    )
    context.risk_penalty_result = (  # type: ignore[attr-defined]
        risk_penalty_result or _sample_risk_penalty_result()
    )
    return context


def build_scorer(*, logger: ScaffoldRecoLogger | None = None) -> FinalScoreCalculator:
    if logger is None:
        return build_default_final_score_calculator()
    return FinalScoreCalculator(logger=logger)


def run_scoring_from_context(
    context: ExecutionContext,
) -> tuple[FinalScoreResult, FinalScoreCalculatorRunMetrics]:
    scorer = build_scorer()
    return scorer.calculate_final_score(context)
