"""MOD-RECO-022 Result Snapshot Builder smoke tests (implementation Task)."""

from __future__ import annotations

import pytest

from conftest import (
    DEFAULT_ITEM_ID,
    DEFAULT_RESULT_ID,
    _sample_builder_item,
    _sample_context,
    build_snapshot_builder,
)
from reco.application.result_snapshot_builder import (
    ITEM_INFO_ERROR_CODE,
    SURFACE_ERROR_CODE,
    ResultSnapshotBuilderError,
)
from reco.application.result_snapshot_builder.in_memory_repository import (
    InMemoryItemSnapshotReadRepository,
    InMemoryItemSnapshotSource,
    InMemoryRecommendationResultItemRepository,
)


def test_execute_fills_snapshots_and_persists_items() -> None:
    context = _sample_context()
    item_repository = InMemoryRecommendationResultItemRepository()
    builder = build_snapshot_builder(item_repository=item_repository)

    result_context = builder.execute(context)

    assert "MOD-RECO-022" in result_context.completed_modules
    version_info = result_context.recommendation_result.version_info or {}
    assert version_info["snapshot_builder_items_persisted"] == "true"
    assert version_info["snapshot_builder_item_count"] == "1"
    assert version_info[f"item:{DEFAULT_ITEM_ID}:item_name_snapshot"] == "実用的ギフト"
    assert DEFAULT_RESULT_ID in item_repository.rows_by_result_id
    row = item_repository.rows_by_result_id[DEFAULT_RESULT_ID][0]
    assert row.item_name_snapshot == "実用的ギフト"
    assert row.item_price_snapshot == 5000
    assert row.item_url_snapshot == "https://example.com/items/item-001"
    assert row.item_image_url_snapshot == "https://example.com/images/item-001.jpg"
    assert row.review_average_snapshot == pytest.approx(4.0)
    assert row.review_count_snapshot == 120
    assert row.rank == 1
    assert row.final_score == pytest.approx(0.78)
    assert row.context_score == pytest.approx(0.82)


def test_execute_succeeds_without_primary_image() -> None:
    item_reader = InMemoryItemSnapshotReadRepository()
    item_reader.register_item(
        InMemoryItemSnapshotSource(
            item_id=DEFAULT_ITEM_ID,
            item_name="画像なしギフト",
            price=3000,
            item_url="https://example.com/items/item-001",
        ),
    )
    context = _sample_context()
    builder = build_snapshot_builder(item_reader=item_reader)

    result_context = builder.execute(context)

    row = builder.item_repository.rows_by_result_id[DEFAULT_RESULT_ID][0]
    assert row.item_image_url_snapshot is None
    version_info = result_context.recommendation_result.version_info or {}
    assert version_info["snapshot_builder_item_count"] == "1"


def test_execute_raises_when_item_missing() -> None:
    item_reader = InMemoryItemSnapshotReadRepository()
    context = _sample_context()
    builder = build_snapshot_builder(item_reader=item_reader)

    with pytest.raises(ResultSnapshotBuilderError) as exc_info:
        builder.execute(context)

    assert exc_info.value.error_code == ITEM_INFO_ERROR_CODE


def test_execute_raises_when_items_count_mismatch() -> None:
    context = _sample_context()
    assert context.recommendation_result is not None
    context.recommendation_result.version_info["result_item_count"] = "2"
    builder = build_snapshot_builder()

    with pytest.raises(ResultSnapshotBuilderError) as exc_info:
        builder.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_when_insert_fails() -> None:
    item_repository = InMemoryRecommendationResultItemRepository(
        should_fail_on_insert=True,
    )
    context = _sample_context()
    builder = build_snapshot_builder(item_repository=item_repository)

    with pytest.raises(ResultSnapshotBuilderError) as exc_info:
        builder.execute(context)

    assert exc_info.value.error_code == "GRS-RES-003"


def test_execute_echoes_score_columns_from_input() -> None:
    item = _sample_builder_item(rank=2, final_score=0.91, context_score=0.88)
    context = _sample_context(items=(item,))
    builder = build_snapshot_builder()

    builder.execute(context)

    row = builder.item_repository.rows_by_result_id[DEFAULT_RESULT_ID][0]
    assert row.rank == 2
    assert row.final_score == pytest.approx(0.91)
    assert row.context_score == pytest.approx(0.88)
    assert row.recommendation_result_item_id == item.recommendation_result_item_id
