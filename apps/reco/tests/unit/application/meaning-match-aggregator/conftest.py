"""Test bootstrap and shared fixtures for MOD-RECO-015 unit tests."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

from reco.application.config_version_resolver import (
    DEFAULT_EMBEDDING_MODEL_VERSION_ID,
    DEFAULT_MATCHING_CONFIG_ID,
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
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES


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

from reco.application.feature_matcher.models import (  # noqa: E402
    FeatureAxisMatch,
    FeatureMatchEntry,
    FeatureMatchResult,
)
from reco.application.meaning_match_aggregator import (  # noqa: E402
    AGGREGATION_METHOD_WEIGHTED_AVERAGE,
    MeaningMatchAggregator,
)
from reco.application.meaning_match_aggregator.models import (  # noqa: E402
    MeaningMatchAggregatorRunMetrics,
    MeaningMatchResult,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger  # noqa: E402

DEFAULT_RUN_ID = "run-meaning-match-aggregator-1"


def _default_config_versions() -> dict[str, str]:
    versions: dict[str, str] = {
        "semantic_config_version_id": DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        "model_versions.embedding": DEFAULT_EMBEDDING_MODEL_VERSION_ID,
        "matching_config_id": DEFAULT_MATCHING_CONFIG_ID,
    }
    for feature_code in ("formality", "safety", "brand_appropriateness"):
        versions[f"social_feature_weights.{feature_code}"] = "0.333"
    for feature_code in (
        "emotion",
        "novelty",
        "intimacy",
        "symbolic_identity",
        "story_richness",
    ):
        versions[f"symbolic_feature_weights.{feature_code}"] = "0.2"
    return versions


def _axis_matches_uniform(match_value: float) -> dict[str, float]:
    return {axis: match_value for axis in MVP_FEATURE_CODES}


def _feature_match_entry(
    *,
    item_id: str,
    match_value: float,
    matching_config_id: str = DEFAULT_MATCHING_CONFIG_ID,
) -> FeatureMatchEntry:
    return _feature_match_entry_with_matches(
        item_id=item_id,
        axis_matches=_axis_matches_uniform(match_value),
        matching_config_id=matching_config_id,
    )


def _feature_match_entry_with_matches(
    *,
    item_id: str,
    axis_matches: dict[str, float],
    matching_config_id: str = DEFAULT_MATCHING_CONFIG_ID,
    distance_overrides: dict[str, float] | None = None,
) -> FeatureMatchEntry:
    features: dict[str, FeatureAxisMatch] = {}
    for axis in MVP_FEATURE_CODES:
        match = axis_matches[axis]
        distance = (
            distance_overrides[axis]
            if distance_overrides and axis in distance_overrides
            else 1.0 - match
        )
        features[axis] = FeatureAxisMatch(distance=distance, match=match)
    return FeatureMatchEntry(
        item_id=item_id,
        features=features,
        meaning_distance=0.1,
        calculated_at=datetime.now(UTC),
        matching_config_id=matching_config_id,
    )


def _sample_feature_match_result(
    *,
    entries: tuple[FeatureMatchEntry, ...] | None = None,
) -> FeatureMatchResult:
    resolved_entries = entries or (
        _feature_match_entry(item_id="item-001", match_value=0.92),
        _feature_match_entry(item_id="item-002", match_value=0.85),
    )
    return FeatureMatchResult(
        entries=resolved_entries,
        total_matched=len(resolved_entries),
        total_excluded=0,
    )


def _sample_context(
    *,
    run_id: str = DEFAULT_RUN_ID,
    feature_match_result: FeatureMatchResult | None = None,
    config_versions: dict[str, str] | None = None,
    trace_id: str = "trace-meaning-match-aggregator",
) -> ExecutionContext:
    request = RecommendationRequest(
        request_id="req-meaning-match-aggregator-1",
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
            model_version=DEFAULT_EMBEDDING_MODEL_VERSION_ID,
        ),
    )
    context.feature_match_result = feature_match_result or _sample_feature_match_result()  # type: ignore[attr-defined]
    return context


def build_aggregator(
    *,
    logger: ScaffoldRecoLogger | None = None,
) -> MeaningMatchAggregator:
    if logger is None:
        return MeaningMatchAggregator()
    return MeaningMatchAggregator(logger=logger)


def run_aggregation_from_context(
    context: ExecutionContext,
) -> tuple[MeaningMatchResult, MeaningMatchAggregatorRunMetrics]:
    aggregator = build_aggregator()
    return aggregator.aggregate_meaning_match(context)
