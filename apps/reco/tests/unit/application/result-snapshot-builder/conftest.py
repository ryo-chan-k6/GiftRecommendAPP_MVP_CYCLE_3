"""Test bootstrap and shared fixtures for MOD-RECO-022 unit tests."""

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
    SnapshotBuilderRunMetrics,
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
    run_id: str = DEFAULT_RUN_ID,
    trace_id: str = "trace-snapshot-builder",
) -> ExecutionContext:
    builder_items = (_sample_builder_item(),) if items is None else items
    version_info = {
        "recommendation_result_id": DEFAULT_RESULT_ID,
        "result_item_count": str(len(builder_items)),
        BUILDER_ITEMS_VERSION_INFO_KEY: encode_builder_items(builder_items),
    }
    context = ExecutionContext(
        recommendation_request=RecommendationRequest(request_id="req-001"),
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
    )
    return context


def build_snapshot_builder(
    *,
    item_reader: InMemoryItemSnapshotReadRepository | None = None,
    item_repository: InMemoryRecommendationResultItemRepository | None = None,
    logger: ScaffoldRecoLogger | None = None,
) -> ResultSnapshotBuilder:
    return ResultSnapshotBuilder(
        item_reader=item_reader or _default_item_reader(),
        item_repository=item_repository or InMemoryRecommendationResultItemRepository(),
        logger=logger or ScaffoldRecoLogger(),
    )


def _default_item_source(
    *,
    item_id: str = DEFAULT_ITEM_ID,
    item_name: str = "実用的ギフト",
    price: int = 5000,
    item_url: str = "https://example.com/items/item-001",
    catchcopy: str | None = "毎日使える定番ギフト",
    shop_code: str | None = "shop-001",
    primary_image_url: str | None = "https://example.com/images/item-001.jpg",
    review_summary: ItemReviewSummary | None = ItemReviewSummary(
        review_average=4.0,
        review_count=120,
    ),
) -> InMemoryItemSnapshotSource:
    return InMemoryItemSnapshotSource(
        item_id=item_id,
        item_name=item_name,
        price=price,
        item_url=item_url,
        catchcopy=catchcopy,
        shop_code=shop_code,
        primary_image_url=primary_image_url,
        review_summary=review_summary,
    )


def _item_reader_with_sources(
    *sources: InMemoryItemSnapshotSource,
) -> InMemoryItemSnapshotReadRepository:
    repo = InMemoryItemSnapshotReadRepository()
    for source in sources:
        repo.register_item(source)
    return repo


def _default_item_reader() -> InMemoryItemSnapshotReadRepository:
    return _item_reader_with_sources(_default_item_source())


def run_build_snapshots_from_context(
    context: ExecutionContext,
    *,
    item_reader: InMemoryItemSnapshotReadRepository | None = None,
    item_repository: InMemoryRecommendationResultItemRepository | None = None,
) -> tuple[tuple[SnapshotBuilderInputItem, ...], SnapshotBuilderRunMetrics]:
    builder = build_snapshot_builder(
        item_reader=item_reader,
        item_repository=item_repository,
    )
    return builder.build_snapshots(context)
