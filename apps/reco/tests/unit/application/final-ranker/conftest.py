"""Test bootstrap and shared fixtures for MOD-RECO-020 smoke tests."""

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
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES
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
    "reco.application.feature_matcher",
    "src/reco/application/feature-matcher",
)
_load_package(
    "reco.application.final_score_calculator",
    "src/reco/application/final-score-calculator",
)
_load_package(
    "reco.application.final_ranker",
    "src/reco/application/final-ranker",
)

from reco.application.feature_matcher.models import (  # noqa: E402
    FeatureAxisMatch,
    FeatureMatchEntry,
    FeatureMatchResult,
)
from reco.application.final_ranker import (  # noqa: E402
    FinalRanker,
    build_default_final_ranker,
)
from reco.application.final_score_calculator.models import (  # noqa: E402
    FinalScoreEntry,
    FinalScoreResult,
    RankingWeightsUsed,
)

DEFAULT_RUN_ID = "run-final-ranker-1"


def _default_config_versions() -> dict[str, str]:
    return {
        "ranking_config_id": DEFAULT_RANKING_CONFIG_ID,
        "lambda_mmr": "0.75",
        "mmr_candidate_limit": "50",
        "top_k_default": "10",
        "diversity_method": "mmr",
    }


def _uniform_features(value: float = 0.8) -> dict[str, FeatureAxisMatch]:
    return {
        axis: FeatureAxisMatch(distance=1.0 - value, match=value)
        for axis in MVP_FEATURE_CODES
    }


def _final_score_entry(
    *,
    item_id: str,
    pre_rank_score: float = 0.722,
    final_score: float | None = None,
) -> FinalScoreEntry:
    resolved_final = final_score if final_score is not None else pre_rank_score
    return FinalScoreEntry(
        item_id=item_id,
        context_score=0.84,
        popularity_score=0.72,
        risk_penalty=0.10,
        pre_rank_score=pre_rank_score,
        diversity_penalty=0.0,
        final_score=resolved_final,
        score_breakdown={
            "pre_rank_score": pre_rank_score,
            "final_score": resolved_final,
            "diversity": {"penalty": 0.0},
        },
        final_score_formula="linear_weighted_v1",
        ranking_weights_used=RankingWeightsUsed(
            w_context=0.70,
            w_popularity=0.20,
            w_risk=0.10,
        ),
        calculated_at=datetime.now(UTC),
        ranking_config_id=DEFAULT_RANKING_CONFIG_ID,
    )


def _feature_match_entry(
    *,
    item_id: str,
    match_value: float = 0.8,
) -> FeatureMatchEntry:
    return FeatureMatchEntry(
        item_id=item_id,
        features=_uniform_features(match_value),
        meaning_distance=0.2,
        calculated_at=datetime.now(UTC),
        matching_config_id="c1111111-1111-4111-8111-111111111102",
    )


def _sample_final_score_result(
    *,
    entries: tuple[FinalScoreEntry, ...] | None = None,
) -> FinalScoreResult:
    resolved_entries = entries or (_final_score_entry(item_id="item-001"),)
    return FinalScoreResult(
        entries=resolved_entries,
        total_scored=len(resolved_entries),
    )


def _sample_feature_match_result(
    *,
    entries: tuple[FeatureMatchEntry, ...] | None = None,
) -> FeatureMatchResult:
    resolved_entries = entries or (_feature_match_entry(item_id="item-001"),)
    return FeatureMatchResult(
        entries=resolved_entries,
        total_matched=len(resolved_entries),
        total_excluded=0,
    )


def _sample_context(
    *,
    run_id: str = DEFAULT_RUN_ID,
    final_score_result: FinalScoreResult | None = None,
    feature_match_result: FeatureMatchResult | None = None,
    config_versions: dict[str, str] | None = None,
    top_k: int | None = None,
    trace_id: str = "trace-final-ranker",
) -> ExecutionContext:
    request = RecommendationRequest(
        request_id="req-final-ranker-1",
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
            top_k=top_k,
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
    )
    context.final_score_result = (  # type: ignore[attr-defined]
        final_score_result or _sample_final_score_result()
    )
    context.feature_match_result = (
        feature_match_result or _sample_feature_match_result()
    )
    return context


def build_ranker(*, logger: ScaffoldRecoLogger | None = None) -> FinalRanker:
    if logger is None:
        return build_default_final_ranker()
    return FinalRanker(logger=logger)
