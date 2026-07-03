"""Test bootstrap and shared fixtures for MOD-RECO-018 unit tests."""

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
    "reco.application.feature_matcher",
    "src/reco/application/feature-matcher",
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

from reco.application.feature_matcher.models import (  # noqa: E402
    FeatureAxisMatch,
    FeatureMatchEntry,
    FeatureMatchResult,
)
from reco.application.meaning_match_aggregator.models import (  # noqa: E402
    MeaningMatchEntry,
    MeaningMatchResult,
)
from reco.application.popularity_scorer.models import (  # noqa: E402
    PopularityScoreEntry,
    PopularityScoreResult,
)
from reco.application.risk_scorer import (  # noqa: E402
    RiskScorer,
    build_default_risk_scorer,
)

DEFAULT_RUN_ID = "run-risk-scorer-1"
DEFAULT_MATCHING_CONFIG_ID = "c1111111-1111-4111-8111-111111111102"


def _default_config_versions() -> dict[str, str]:
    return {
        "ranking_config_id": DEFAULT_RANKING_CONFIG_ID,
        "risk_formula": "avoid_social_data_quality_weighted",
        "risk_weights.avoid": "0.50",
        "risk_weights.social": "0.30",
        "risk_weights.data_quality": "0.20",
        "social_threshold": "0.60",
    }


def _feature_axis_matches(
    *,
    imputed_axes: tuple[str, ...] = (),
) -> dict[str, FeatureAxisMatch]:
    return {
        axis: FeatureAxisMatch(
            distance=0.1,
            match=0.9,
            imputed=axis in imputed_axes,
        )
        for axis in MVP_FEATURE_CODES
    }


def _feature_match_entry(
    *,
    item_id: str,
    avoid_similarity: float | None = 0.30,
    imputed_axes: tuple[str, ...] = ("formality", "safety"),
) -> FeatureMatchEntry:
    return FeatureMatchEntry(
        item_id=item_id,
        features=_feature_axis_matches(imputed_axes=imputed_axes),
        meaning_distance=1.0,
        calculated_at=datetime.now(UTC),
        matching_config_id=DEFAULT_MATCHING_CONFIG_ID,
        avoid_similarity=avoid_similarity,
    )


def _meaning_match_entry(
    *,
    item_id: str,
    social_match: float = 0.45,
) -> MeaningMatchEntry:
    return MeaningMatchEntry(
        item_id=item_id,
        social_match=social_match,
        symbolic_match=0.7,
        aggregation_method="weighted_average",
        calculated_at=datetime.now(UTC),
        matching_config_id=DEFAULT_MATCHING_CONFIG_ID,
    )


def _popularity_score_entry(
    *,
    item_id: str,
    popularity_score: float = 0.75,
) -> PopularityScoreEntry:
    return PopularityScoreEntry(
        item_id=item_id,
        popularity_score=popularity_score,
        popularity_formula="rating_review_count_weighted",
        calculated_at=datetime.now(UTC),
        ranking_config_id=DEFAULT_RANKING_CONFIG_ID,
        signal_missing=False,
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


def _sample_meaning_match_result(
    *,
    entries: tuple[MeaningMatchEntry, ...] | None = None,
) -> MeaningMatchResult:
    resolved_entries = entries or (_meaning_match_entry(item_id="item-001"),)
    return MeaningMatchResult(
        entries=resolved_entries,
        total_aggregated=len(resolved_entries),
    )


def _sample_context(
    *,
    run_id: str = DEFAULT_RUN_ID,
    popularity_score_result: PopularityScoreResult | None = None,
    feature_match_result: FeatureMatchResult | None = None,
    meaning_match_result: MeaningMatchResult | None = None,
    config_versions: dict[str, str] | None = None,
    trace_id: str = "trace-risk-scorer",
) -> ExecutionContext:
    request = RecommendationRequest(
        request_id="req-risk-scorer-1",
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
    context.popularity_score_result = (  # type: ignore[attr-defined]
        popularity_score_result or _sample_popularity_score_result()
    )
    context.feature_match_result = feature_match_result or _sample_feature_match_result()
    context.meaning_match_result = meaning_match_result or _sample_meaning_match_result()
    return context


def build_scorer(*, logger: ScaffoldRecoLogger | None = None) -> RiskScorer:
    if logger is None:
        return build_default_risk_scorer()
    return RiskScorer(logger=logger)
