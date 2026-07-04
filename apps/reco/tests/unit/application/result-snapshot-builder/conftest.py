"""Test bootstrap and shared fixtures for MOD-RECO-022 smoke tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from uuid import uuid4

from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)
from reco.domain.recommendation.inputs import ExecutionMode
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

from reco.application.result_snapshot_builder import (  # noqa: E402
    BUILDER_ITEMS_VERSION_INFO_KEY,
    InMemoryItemSnapshotReadRepository,
    InMemoryItemSnapshotSource,
    InMemoryRecommendationResultItemRepository,
    ResultSnapshotBuilder,
    SnapshotBuilderInputItem,
    build_default_result_snapshot_builder,
    encode_builder_items,
)
from reco.application.popularity_scorer.models import ItemReviewSummary  # noqa: E402

DEFAULT_RUN_ID = "run-snapshot-builder-1"
DEFAULT_RESULT_ID = "result-snapshot-builder-1"
DEFAULT_ITEM_ID = "item-001"


def _sample_builder_item(
    *,
    item_id: str = DEFAULT_ITEM_ID,
    rank: int = 1,
    final_score: float = 0.78,
    context_score: float = 0.82,
) -> SnapshotBuilderInputItem:
    return SnapshotBuilderInputItem(
        recommendation_result_item_id=str(uuid4()),
        recommendation_result_id=DEFAULT_RESULT_ID,
        item_id=item_id,
        rank=rank,
        final_score=final_score,
        context_score=context_score,
        score_breakdown_json={"final_score": {"value": final_score}},
        is_displayed=True,
        is_fallback=False,
    )


def _sample_context(
    *,
    items: tuple[SnapshotBuilderInputItem, ...] | None = None,
) -> ExecutionContext:
    builder_items = items or (_sample_builder_item(),)
    version_info = {
        "recommendation_result_id": DEFAULT_RESULT_ID,
        "result_item_count": str(len(builder_items)),
        BUILDER_ITEMS_VERSION_INFO_KEY: encode_builder_items(builder_items),
    }
    context = ExecutionContext(
        recommendation_request=RecommendationRequest(request_id="req-001"),
        trace_id="trace-snapshot-builder",
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
    )
    return context


def build_snapshot_builder(
    *,
    item_reader: InMemoryItemSnapshotReadRepository | None = None,
    item_repository: InMemoryRecommendationResultItemRepository | None = None,
) -> ResultSnapshotBuilder:
    return ResultSnapshotBuilder(
        item_reader=item_reader or _default_item_reader(),
        item_repository=item_repository or InMemoryRecommendationResultItemRepository(),
        logger=ScaffoldRecoLogger(),
    )


def _default_item_reader() -> InMemoryItemSnapshotReadRepository:
    repo = InMemoryItemSnapshotReadRepository()
    repo.register_item(
        InMemoryItemSnapshotSource(
            item_id=DEFAULT_ITEM_ID,
            item_name="実用的ギフト",
            price=5000,
            item_url="https://example.com/items/item-001",
            catchcopy="毎日使える定番ギフト",
            shop_code="shop-001",
            primary_image_url="https://example.com/images/item-001.jpg",
            review_summary=ItemReviewSummary(review_average=4.0, review_count=120),
        ),
    )
    return repo
