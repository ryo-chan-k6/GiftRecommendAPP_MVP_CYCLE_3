"""Snapshot build logic for MOD-RECO-022."""

from __future__ import annotations

from .constants import (
    ITEM_INFO_ERROR_CODE,
    RESULT_ITEM_SAVE_ERROR_CODE,
    SNAPSHOT_BUILD_ERROR_CODE,
    SURFACE_ERROR_CODE,
)
from .errors import ResultSnapshotBuilderError
from .models import (
    ItemSnapshot,
    ItemSourceRecord,
    RecommendationResultItemInsertRow,
    SnapshotBuilderInput,
    SnapshotBuilderInputItem,
    SnapshotBuilderRunMetrics,
)
from .ports import ItemSnapshotReadPort, RecommendationResultItemRepositoryPort


def build_result_snapshots(
    snapshot_input: SnapshotBuilderInput,
    *,
    item_reader: ItemSnapshotReadPort,
    item_repository: RecommendationResultItemRepositoryPort,
) -> tuple[tuple[SnapshotBuilderInputItem, ...], SnapshotBuilderRunMetrics]:
    """Item 正本読取 → Snapshot 充填 → recommendation_result_item INSERT。"""
    item_ids = tuple(item.item_id for item in snapshot_input.items)

    try:
        item_sources = item_reader.fetch_items(item_ids)
        primary_images = item_reader.fetch_primary_images(item_ids)
        review_snapshots = item_reader.fetch_review_snapshots(item_ids)
    except Exception as exc:  # noqa: BLE001
        raise ResultSnapshotBuilderError(
            "item snapshot source fetch failed",
            error_code=SNAPSHOT_BUILD_ERROR_CODE,
        ) from exc

    filled_items: list[SnapshotBuilderInputItem] = []
    insert_rows: list[RecommendationResultItemInsertRow] = []
    null_image_count = 0
    null_review_count = 0

    for item in snapshot_input.items:
        source = item_sources.get(item.item_id)
        if source is None:
            raise ResultSnapshotBuilderError(
                f"item not found for item_id: {item.item_id}",
                error_code=ITEM_INFO_ERROR_CODE,
            )

        snapshot = _map_snapshot(
            source=source,
            primary_image=primary_images.get(item.item_id),
            review=review_snapshots.get(item.item_id),
        )
        if snapshot.item_image_url_snapshot is None:
            null_image_count += 1
        if (
            snapshot.review_average_snapshot is None
            and snapshot.review_count_snapshot is None
        ):
            null_review_count += 1

        filled_item = SnapshotBuilderInputItem(
            recommendation_result_item_id=item.recommendation_result_item_id,
            recommendation_result_id=item.recommendation_result_id,
            item_id=item.item_id,
            rank=item.rank,
            final_score=item.final_score,
            context_score=item.context_score,
            score_breakdown_json=item.score_breakdown_json,
            is_displayed=item.is_displayed,
            is_fallback=item.is_fallback,
            snapshot=snapshot,
        )
        filled_items.append(filled_item)
        insert_rows.append(_to_insert_row(filled_item))

    try:
        inserted_count = item_repository.insert_items(tuple(insert_rows))
    except Exception as exc:  # noqa: BLE001
        raise ResultSnapshotBuilderError(
            "recommendation_result_item insert failed",
            error_code=RESULT_ITEM_SAVE_ERROR_CODE,
        ) from exc

    if inserted_count != snapshot_input.result_item_count:
        raise ResultSnapshotBuilderError(
            "inserted item count does not match result_item_count",
            error_code=SURFACE_ERROR_CODE,
        )

    metrics = SnapshotBuilderRunMetrics(
        snapshot_builder_item_count=inserted_count,
        snapshot_builder_latency_ms=0,
        snapshot_builder_items_persisted=True,
        snapshot_build_success=True,
        snapshot_null_image_count=null_image_count,
        snapshot_null_review_count=null_review_count,
    )
    return tuple(filled_items), metrics


def _map_snapshot(
    *,
    source: ItemSourceRecord,
    primary_image: object | None,
    review: object | None,
) -> ItemSnapshot:
    if not source.item_name:
        raise ResultSnapshotBuilderError(
            f"item_name missing for item_id: {source.item_id}",
            error_code=ITEM_INFO_ERROR_CODE,
        )
    if source.price is None or source.price < 0:
        raise ResultSnapshotBuilderError(
            f"item_price invalid for item_id: {source.item_id}",
            error_code=ITEM_INFO_ERROR_CODE,
        )
    if not source.item_url:
        raise ResultSnapshotBuilderError(
            f"item_url missing for item_id: {source.item_id}",
            error_code=ITEM_INFO_ERROR_CODE,
        )

    image_url = None
    if primary_image is not None:
        image_url = getattr(primary_image, "image_url", None)

    review_average = None
    review_count = None
    if review is not None:
        review_average = getattr(review, "review_average", None)
        review_count = getattr(review, "review_count", None)

    shop_name = source.shop_code if source.shop_code else None

    return ItemSnapshot(
        item_name_snapshot=source.item_name,
        item_price_snapshot=source.price,
        item_url_snapshot=source.item_url,
        item_image_url_snapshot=image_url,
        item_catchcopy_snapshot=source.catchcopy,
        shop_name_snapshot=shop_name,
        review_average_snapshot=review_average,
        review_count_snapshot=review_count,
    )


def _to_insert_row(item: SnapshotBuilderInputItem) -> RecommendationResultItemInsertRow:
    if item.snapshot is None:
        raise ResultSnapshotBuilderError(
            f"snapshot missing for item_id: {item.item_id}",
            error_code=SNAPSHOT_BUILD_ERROR_CODE,
        )

    snapshot = item.snapshot
    return RecommendationResultItemInsertRow(
        recommendation_result_item_id=item.recommendation_result_item_id,
        recommendation_result_id=item.recommendation_result_id,
        item_id=item.item_id,
        rank=item.rank,
        final_score=item.final_score,
        context_score=item.context_score,
        score_breakdown_json=item.score_breakdown_json,
        is_displayed=item.is_displayed,
        is_fallback=item.is_fallback,
        item_name_snapshot=snapshot.item_name_snapshot,
        item_price_snapshot=snapshot.item_price_snapshot,
        item_url_snapshot=snapshot.item_url_snapshot,
        item_image_url_snapshot=snapshot.item_image_url_snapshot,
        item_catchcopy_snapshot=snapshot.item_catchcopy_snapshot,
        shop_name_snapshot=snapshot.shop_name_snapshot,
        review_average_snapshot=snapshot.review_average_snapshot,
        review_count_snapshot=snapshot.review_count_snapshot,
    )
