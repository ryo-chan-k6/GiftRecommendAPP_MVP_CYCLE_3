"""Test bootstrap and shared fixtures for MOD-RECO-023 unit tests."""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

from reco.application.feature_matcher.models import (
    FeatureAxisMatch,
    FeatureMatchEntry,
    FeatureMatchResult,
)
from reco.application.meaning_match_aggregator.models import (
    MeaningMatchEntry,
    MeaningMatchResult,
)
from reco.application.risk_scorer.models import RiskPenaltyEntry, RiskPenaltyResult
from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)
from reco.domain.recommendation.inputs import ExecutionMode, OccasionCondition, RelationshipCondition
from reco.domain.recommendation.request import RecommendationRequest
from reco.domain.recommendation.result import RecommendationResult, RecommendationResultItem, ResultStatus
from reco.domain.recommendation.run import RecommendationRun, RunStatus
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
    "reco.application.result_snapshot_builder",
    "src/reco/application/result-snapshot-builder",
)
_load_package(
    "reco.application.reason_generator",
    "src/reco/application/reason-generator",
)

from reco.application.reason_generator import (  # noqa: E402
    InMemoryItemSemanticReadRepository,
    InMemoryReasonTemplateReadRepository,
    InMemoryRecommendationReasonRepository,
    ItemSemanticRecord,
    ReasonGenerator,
    ReasonTemplateRecord,
    SemanticEvidence,
    build_default_in_memory_reason_template_repository,
)
from reco.application.result_snapshot_builder.models import SnapshotBuilderInputItem  # noqa: E402
from reco.application.result_snapshot_builder.input_parser import encode_builder_items  # noqa: E402
from reco.infrastructure.external_ai.client import ExternalAiClient, ScaffoldExternalAiClient  # noqa: E402

DEFAULT_RUN_ID = "run-reason-generator-1"
DEFAULT_RESULT_ID = "result-reason-generator-1"
DEFAULT_ITEM_ID = "item-001"
DEFAULT_RESULT_ITEM_ID = "result-item-001"
DEFAULT_MATCHING_CONFIG_ID = "matching-config-1"
DEFAULT_RANKING_CONFIG_ID = "ranking-config-1"
DEFAULT_SEMANTIC_CONFIG_VERSION_ID = "semantic-config-v1"


def _sample_builder_item(
    *,
    item_id: str = DEFAULT_ITEM_ID,
    recommendation_result_item_id: str = DEFAULT_RESULT_ITEM_ID,
    rank: int = 1,
    final_score: float = 0.84,
    context_score: float = 0.82,
) -> SnapshotBuilderInputItem:
    return SnapshotBuilderInputItem(
        recommendation_result_item_id=recommendation_result_item_id,
        recommendation_result_id=DEFAULT_RESULT_ID,
        item_id=item_id,
        rank=rank,
        final_score=final_score,
        context_score=context_score,
        score_breakdown_json={"final_score": {"value": final_score}},
        is_displayed=True,
        is_fallback=False,
    )


def _feature_match_entry(
    *,
    item_id: str = DEFAULT_ITEM_ID,
    features: dict[str, FeatureAxisMatch] | None = None,
    avoid_similarity: float | None = None,
) -> FeatureMatchEntry:
    now = datetime.now(timezone.utc)
    return FeatureMatchEntry(
        item_id=item_id,
        features=features
        if features is not None
        else {
            "formality": FeatureAxisMatch(distance=0.1, match=0.88),
            "safety": FeatureAxisMatch(distance=0.15, match=0.85),
            "emotion": FeatureAxisMatch(distance=0.4, match=0.65),
        },
        meaning_distance=0.2,
        calculated_at=now,
        matching_config_id=DEFAULT_MATCHING_CONFIG_ID,
        avoid_similarity=avoid_similarity,
    )


def _sample_feature_match_result(
    *,
    item_id: str = DEFAULT_ITEM_ID,
    entries: tuple[FeatureMatchEntry, ...] | None = None,
) -> FeatureMatchResult:
    resolved_entries = entries or (_feature_match_entry(item_id=item_id),)
    return FeatureMatchResult(
        entries=resolved_entries,
        total_matched=len(resolved_entries),
        total_excluded=0,
    )


def _meaning_match_entry(
    *,
    item_id: str = DEFAULT_ITEM_ID,
    social_match: float = 0.86,
) -> MeaningMatchEntry:
    return MeaningMatchEntry(
        item_id=item_id,
        social_match=social_match,
        symbolic_match=0.76,
        aggregation_method="weighted_average",
        calculated_at=datetime.now(timezone.utc),
        matching_config_id=DEFAULT_MATCHING_CONFIG_ID,
    )


def _sample_meaning_match_result(
    *,
    entries: tuple[MeaningMatchEntry, ...] | None = None,
) -> MeaningMatchResult:
    resolved_entries = entries or (_meaning_match_entry(),)
    return MeaningMatchResult(
        entries=resolved_entries,
        total_aggregated=len(resolved_entries),
    )


def _risk_penalty_entry(
    *,
    item_id: str = DEFAULT_ITEM_ID,
    risk_penalty: float = 0.08,
) -> RiskPenaltyEntry:
    return RiskPenaltyEntry(
        item_id=item_id,
        risk_penalty=risk_penalty,
        risk_formula="weighted_sum",
        calculated_at=datetime.now(timezone.utc),
        ranking_config_id=DEFAULT_RANKING_CONFIG_ID,
        signal_missing=False,
    )


def _sample_risk_penalty_result(
    *,
    entries: tuple[RiskPenaltyEntry, ...] | None = None,
) -> RiskPenaltyResult:
    resolved_entries = entries or (_risk_penalty_entry(),)
    return RiskPenaltyResult(
        entries=resolved_entries,
        total_scored=len(resolved_entries),
    )


def _sample_item_semantic_record(
    *,
    item_id: str = DEFAULT_ITEM_ID,
    evidence_text: str = "落ち着いた包装で贈りやすい",
) -> ItemSemanticRecord:
    return ItemSemanticRecord(
        item_id=item_id,
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        concepts=(
            SemanticEvidence(
                concept_code="gift_presentation",
                evidence_text=evidence_text,
                confidence=0.91,
            ),
        ),
    )


def build_item_semantic_reader(
    *records: ItemSemanticRecord,
) -> InMemoryItemSemanticReadRepository:
    reader = InMemoryItemSemanticReadRepository()
    for record in records:
        reader.register(record)
    return reader


def build_template_repository(
    *templates: ReasonTemplateRecord,
) -> InMemoryReasonTemplateReadRepository:
    if templates:
        return InMemoryReasonTemplateReadRepository(templates=templates)
    return build_default_in_memory_reason_template_repository()


def _sample_context(
    *,
    items: tuple[SnapshotBuilderInputItem, ...] | None = None,
    include_feature_match: bool = True,
    feature_match_result: FeatureMatchResult | None = None,
    meaning_match_result: MeaningMatchResult | None = None,
    risk_penalty_result: RiskPenaltyResult | None = None,
    relationship: RelationshipCondition | None = RelationshipCondition(
        relationship_code="friend",
        relationship_label="友人",
    ),
    occasion: OccasionCondition | None = OccasionCondition(
        occasion_code="birthday",
        occasion_label="誕生日",
    ),
    trace_id: str = "trace-reason-generator",
    run_id: str = DEFAULT_RUN_ID,
    config_versions: dict[str, str] | None = None,
) -> ExecutionContext:
    builder_items = items or (_sample_builder_item(),)
    version_info = {
        "recommendation_result_id": DEFAULT_RESULT_ID,
        "result_item_count": str(len(builder_items)),
        "snapshot_builder_items_persisted": "true",
        "_builder_items": encode_builder_items(builder_items),
    }
    context = ExecutionContext(
        recommendation_request=RecommendationRequest(
            request_id="req-001",
            relationship=relationship,
            occasion=occasion,
        ),
        trace_id=trace_id,
        execution_mode=ExecutionMode.UI,
        recommendation_run=RecommendationRun(
            run_id=run_id,
            request_id="req-001",
            status=RunStatus.RUNNING,
        ),
        recommendation_result=RecommendationResult(
            run_id=DEFAULT_RUN_ID,
            request_id="req-001",
            items=tuple(
                RecommendationResultItem(
                    item_id=item.item_id,
                    rank=item.rank,
                    final_score=item.final_score,
                    is_fallback=item.is_fallback,
                )
                for item in builder_items
            ),
            result_status=ResultStatus.COMPLETED,
            version_info=version_info,
        ),
        config_versions=config_versions
        or {"semantic_config_version_id": DEFAULT_SEMANTIC_CONFIG_VERSION_ID},
    )
    if include_feature_match:
        context.feature_match_result = (
            feature_match_result if feature_match_result is not None else _sample_feature_match_result()
        )
    if meaning_match_result is not None:
        context.meaning_match_result = meaning_match_result
    if risk_penalty_result is not None:
        context.risk_penalty_result = risk_penalty_result
    return context


def build_reason_generator(
    *,
    reason_repository: InMemoryRecommendationReasonRepository | None = None,
    template_reader: InMemoryReasonTemplateReadRepository | None = None,
    item_semantic_reader: InMemoryItemSemanticReadRepository | None = None,
    llm_client: ExternalAiClient | None = None,
    logger: ScaffoldRecoLogger | None = None,
) -> ReasonGenerator:
    return ReasonGenerator(
        template_reader=template_reader or build_default_in_memory_reason_template_repository(),
        item_semantic_reader=item_semantic_reader or InMemoryItemSemanticReadRepository(),
        reason_repository=reason_repository or InMemoryRecommendationReasonRepository(),
        llm_client=llm_client if llm_client is not None else ScaffoldExternalAiClient(),
        logger=logger or ScaffoldRecoLogger(),
    )
