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
    InMemoryRecommendationReasonRepository,
    ReasonGenerator,
    build_default_reason_generator,
)
from reco.application.result_snapshot_builder.models import SnapshotBuilderInputItem  # noqa: E402
from reco.application.result_snapshot_builder.input_parser import encode_builder_items  # noqa: E402

DEFAULT_RUN_ID = "run-reason-generator-1"
DEFAULT_RESULT_ID = "result-reason-generator-1"
DEFAULT_ITEM_ID = "item-001"
DEFAULT_RESULT_ITEM_ID = "result-item-001"


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


def _sample_feature_match_result(
    *,
    item_id: str = DEFAULT_ITEM_ID,
) -> FeatureMatchResult:
    now = datetime.now(timezone.utc)
    return FeatureMatchResult(
        entries=(
            FeatureMatchEntry(
                item_id=item_id,
                features={
                    "formality": FeatureAxisMatch(distance=0.1, match=0.88),
                    "safety": FeatureAxisMatch(distance=0.15, match=0.85),
                    "emotion": FeatureAxisMatch(distance=0.4, match=0.65),
                },
                meaning_distance=0.2,
                calculated_at=now,
                matching_config_id="matching-config-1",
            ),
        ),
        total_matched=1,
        total_excluded=0,
    )


def _sample_context(
    *,
    items: tuple[SnapshotBuilderInputItem, ...] | None = None,
    include_feature_match: bool = True,
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
            relationship=RelationshipCondition(
                relationship_code="friend",
                relationship_label="友人",
            ),
            occasion=OccasionCondition(
                occasion_code="birthday",
                occasion_label="誕生日",
            ),
        ),
        trace_id="trace-reason-generator",
        execution_mode=ExecutionMode.UI,
        recommendation_run=RecommendationRun(
            run_id=DEFAULT_RUN_ID,
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
        config_versions={"semantic_config_version_id": "semantic-config-v1"},
    )
    if include_feature_match:
        context.feature_match_result = _sample_feature_match_result()
    return context


def build_reason_generator(
    *,
    reason_repository: InMemoryRecommendationReasonRepository | None = None,
    logger: ScaffoldRecoLogger | None = None,
) -> ReasonGenerator:
    return ReasonGenerator(
        reason_repository=reason_repository or InMemoryRecommendationReasonRepository(),
        logger=logger or ScaffoldRecoLogger(),
    )
