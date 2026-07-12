"""MOD-RECO-022 Result Snapshot Builder unit tests (module spec §14 unit)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

import pytest

from conftest import (
    DEFAULT_ITEM_ID,
    DEFAULT_RESULT_ID,
    _default_item_source,
    _item_reader_with_sources,
    _sample_builder_item,
    _sample_context,
    run_build_snapshots_from_context,
)
from reco.application.result_snapshot_builder import (
    ITEM_INFO_ERROR_CODE,
    RESULT_ITEM_SAVE_ERROR_CODE,
    SURFACE_ERROR_CODE,
    ItemPrimaryImageRecord,
    ItemReviewSnapshotRecord,
    ItemSourceRecord,
    ResultSnapshotBuilderError,
    SnapshotBuilderInput,
    SnapshotBuilderInputItem,
    build_result_snapshots,
)
from reco.application.result_snapshot_builder.in_memory_repository import (
    InMemoryRecommendationResultItemRepository,
)


@dataclass
class _StubItemSnapshotReadPort:
    """Item 正本の欠損パターン検証用スタブ。"""

    items: dict[str, ItemSourceRecord] = field(default_factory=dict)
    primary_images: dict[str, ItemPrimaryImageRecord] = field(default_factory=dict)
    review_snapshots: dict[str, ItemReviewSnapshotRecord] = field(default_factory=dict)
    should_fail_on_fetch: bool = False

    def fetch_items(self, item_ids: tuple[str, ...]) -> dict[str, ItemSourceRecord]:
        if self.should_fail_on_fetch:
            raise RuntimeError("simulated item fetch failure")
        return {item_id: self.items[item_id] for item_id in item_ids if item_id in self.items}

    def fetch_primary_images(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemPrimaryImageRecord]:
        if self.should_fail_on_fetch:
            raise RuntimeError("simulated image fetch failure")
        return {
            item_id: self.primary_images[item_id]
            for item_id in item_ids
            if item_id in self.primary_images
        }

    def fetch_review_snapshots(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemReviewSnapshotRecord]:
        if self.should_fail_on_fetch:
            raise RuntimeError("simulated review fetch failure")
        return {
            item_id: self.review_snapshots[item_id]
            for item_id in item_ids
            if item_id in self.review_snapshots
        }


def _snapshot_input_for_item(
    item: SnapshotBuilderInputItem,
) -> SnapshotBuilderInput:
    return SnapshotBuilderInput(
        recommendation_result_id=item.recommendation_result_id,
        result_item_count=1,
        items=(item,),
    )


# §14 No.1 正常系（全 Item）
def test_build_snapshots_fills_required_snapshot_columns_for_all_items() -> None:
    item_a = _sample_builder_item(item_id="item-a", rank=1)
    item_b = _sample_builder_item(item_id="item-b", rank=2, final_score=0.71, context_score=0.69)
    context = _sample_context(items=(item_a, item_b))
    item_reader = _item_reader_with_sources(
        _default_item_source(item_id="item-a", item_name="ギフトA"),
        _default_item_source(
            item_id="item-b",
            item_name="ギフトB",
            item_url="https://example.com/items/item-b",
            primary_image_url="https://example.com/images/item-b.jpg",
        ),
    )
    item_repository = InMemoryRecommendationResultItemRepository()

    filled_items, metrics = run_build_snapshots_from_context(
        context,
        item_reader=item_reader,
        item_repository=item_repository,
    )

    assert metrics.snapshot_builder_item_count == 2
    assert metrics.snapshot_builder_items_persisted is True
    rows = item_repository.rows_by_result_id[DEFAULT_RESULT_ID]
    assert len(rows) == 2
    for row in rows:
        assert row.item_name_snapshot
        assert row.item_price_snapshot is not None
        assert row.item_url_snapshot
    assert {item.item_id for item in filled_items} == {"item-a", "item-b"}


# §14 No.2 画像あり
def test_build_snapshots_copies_primary_image_url_to_item_image_url_snapshot() -> None:
    context = _sample_context()
    item_reader = _item_reader_with_sources(
        _default_item_source(
            primary_image_url="https://cdn.example.com/primary.jpg",
        ),
    )
    item_repository = InMemoryRecommendationResultItemRepository()

    filled_items, _metrics = run_build_snapshots_from_context(
        context,
        item_reader=item_reader,
        item_repository=item_repository,
    )

    assert filled_items[0].snapshot is not None
    assert filled_items[0].snapshot.item_image_url_snapshot == (
        "https://cdn.example.com/primary.jpg"
    )
    row = item_repository.rows_by_result_id[DEFAULT_RESULT_ID][0]
    assert row.item_image_url_snapshot == "https://cdn.example.com/primary.jpg"


# §14 No.3 画像なし
def test_build_snapshots_succeeds_with_null_item_image_url_snapshot() -> None:
    context = _sample_context()
    item_reader = _item_reader_with_sources(
        _default_item_source(primary_image_url=None),
    )

    filled_items, metrics = run_build_snapshots_from_context(
        context,
        item_reader=item_reader,
    )

    assert filled_items[0].snapshot is not None
    assert filled_items[0].snapshot.item_image_url_snapshot is None
    assert metrics.snapshot_null_image_count == 1


# §14 No.4 レビューあり / なし
def test_build_snapshots_copies_review_snapshots_when_review_summary_exists() -> None:
    context = _sample_context()

    filled_items, metrics = run_build_snapshots_from_context(context)

    snapshot = filled_items[0].snapshot
    assert snapshot is not None
    assert snapshot.review_average_snapshot == pytest.approx(4.0)
    assert snapshot.review_count_snapshot == 120
    assert metrics.snapshot_null_review_count == 0


def test_build_snapshots_sets_null_review_snapshots_when_review_summary_missing() -> None:
    context = _sample_context()
    item_reader = _item_reader_with_sources(
        _default_item_source(review_summary=None),
    )

    filled_items, metrics = run_build_snapshots_from_context(
        context,
        item_reader=item_reader,
    )

    snapshot = filled_items[0].snapshot
    assert snapshot is not None
    assert snapshot.review_average_snapshot is None
    assert snapshot.review_count_snapshot is None
    assert metrics.snapshot_null_review_count == 1


# §14 No.5 catchcopy
def test_build_snapshots_copies_catchcopy_when_present() -> None:
    context = _sample_context()
    item_reader = _item_reader_with_sources(
        _default_item_source(catchcopy="贈り物に最適"),
    )

    filled_items, _metrics = run_build_snapshots_from_context(
        context,
        item_reader=item_reader,
    )

    assert filled_items[0].snapshot is not None
    assert filled_items[0].snapshot.item_catchcopy_snapshot == "贈り物に最適"


def test_build_snapshots_sets_null_catchcopy_when_absent() -> None:
    context = _sample_context()
    item_reader = _item_reader_with_sources(
        _default_item_source(catchcopy=None),
    )

    filled_items, _metrics = run_build_snapshots_from_context(
        context,
        item_reader=item_reader,
    )

    assert filled_items[0].snapshot is not None
    assert filled_items[0].snapshot.item_catchcopy_snapshot is None


# §14 No.6 スコア列不変
def test_build_snapshots_preserves_score_columns_from_builder_input() -> None:
    breakdown = {"final_score": {"value": 0.91}, "context_score": {"value": 0.88}}
    item = _sample_builder_item(
        rank=3,
        final_score=0.91,
        context_score=0.88,
    )
    item = SnapshotBuilderInputItem(
        recommendation_result_item_id=item.recommendation_result_item_id,
        recommendation_result_id=item.recommendation_result_id,
        item_id=item.item_id,
        rank=item.rank,
        final_score=item.final_score,
        context_score=item.context_score,
        score_breakdown_json=breakdown,
        is_displayed=item.is_displayed,
        is_fallback=item.is_fallback,
    )
    context = _sample_context(items=(item,))
    item_repository = InMemoryRecommendationResultItemRepository()

    run_build_snapshots_from_context(context, item_repository=item_repository)

    row = item_repository.rows_by_result_id[DEFAULT_RESULT_ID][0]
    assert row.rank == 3
    assert row.final_score == pytest.approx(0.91)
    assert row.context_score == pytest.approx(0.88)
    assert row.score_breakdown_json == breakdown


# §14 No.7 PK エコー
def test_build_snapshots_preserves_recommendation_result_item_id_from_input() -> None:
    item_id = str(uuid4())
    item = _sample_builder_item()
    item = SnapshotBuilderInputItem(
        recommendation_result_item_id=item_id,
        recommendation_result_id=item.recommendation_result_id,
        item_id=item.item_id,
        rank=item.rank,
        final_score=item.final_score,
        context_score=item.context_score,
        score_breakdown_json=item.score_breakdown_json,
        is_displayed=item.is_displayed,
        is_fallback=item.is_fallback,
    )
    context = _sample_context(items=(item,))
    item_repository = InMemoryRecommendationResultItemRepository()

    run_build_snapshots_from_context(context, item_repository=item_repository)

    row = item_repository.rows_by_result_id[DEFAULT_RESULT_ID][0]
    assert row.recommendation_result_item_id == item_id


# §14 No.8 件数一致（unit）
def test_build_snapshots_insert_count_matches_result_item_count() -> None:
    items = (
        _sample_builder_item(item_id="item-a", rank=1),
        _sample_builder_item(item_id="item-b", rank=2),
    )
    context = _sample_context(items=items)
    item_reader = _item_reader_with_sources(
        _default_item_source(item_id="item-a"),
        _default_item_source(
            item_id="item-b",
            item_url="https://example.com/items/item-b",
        ),
    )
    item_repository = InMemoryRecommendationResultItemRepository()

    _filled, metrics = run_build_snapshots_from_context(
        context,
        item_reader=item_reader,
        item_repository=item_repository,
    )

    assert metrics.snapshot_builder_item_count == 2
    assert len(item_repository.rows_by_result_id[DEFAULT_RESULT_ID]) == 2


# §14 No.9 Item 不存在
def test_build_snapshots_raises_grs_itm_006_when_item_not_found() -> None:
    context = _sample_context()
    item_reader = _item_reader_with_sources()

    with pytest.raises(ResultSnapshotBuilderError) as exc_info:
        run_build_snapshots_from_context(context, item_reader=item_reader)

    assert exc_info.value.error_code == ITEM_INFO_ERROR_CODE


# §14 No.10 必須列欠損
@pytest.mark.parametrize(
    ("field_name", "source"),
    [
        (
            "item_name",
            ItemSourceRecord(
                item_id=DEFAULT_ITEM_ID,
                item_name=None,
                price=1000,
                item_url="https://example.com/items/item-001",
            ),
        ),
        (
            "item_name_empty",
            ItemSourceRecord(
                item_id=DEFAULT_ITEM_ID,
                item_name="",
                price=1000,
                item_url="https://example.com/items/item-001",
            ),
        ),
        (
            "price",
            ItemSourceRecord(
                item_id=DEFAULT_ITEM_ID,
                item_name="ギフト",
                price=None,
                item_url="https://example.com/items/item-001",
            ),
        ),
        (
            "item_url",
            ItemSourceRecord(
                item_id=DEFAULT_ITEM_ID,
                item_name="ギフト",
                price=1000,
                item_url=None,
            ),
        ),
        (
            "item_url_empty",
            ItemSourceRecord(
                item_id=DEFAULT_ITEM_ID,
                item_name="ギフト",
                price=1000,
                item_url="",
            ),
        ),
    ],
)
def test_build_snapshots_raises_grs_itm_006_when_required_item_column_missing(
    field_name: str,
    source: ItemSourceRecord,
) -> None:
    item = _sample_builder_item()
    snapshot_input = _snapshot_input_for_item(item)
    reader = _StubItemSnapshotReadPort(items={DEFAULT_ITEM_ID: source})

    with pytest.raises(ResultSnapshotBuilderError) as exc_info:
        build_result_snapshots(
            snapshot_input,
            item_reader=reader,
            item_repository=InMemoryRecommendationResultItemRepository(),
        )

    assert exc_info.value.error_code == ITEM_INFO_ERROR_CODE


def test_build_snapshots_raises_grs_itm_006_when_price_is_negative() -> None:
    item = _sample_builder_item()
    snapshot_input = _snapshot_input_for_item(item)
    reader = _StubItemSnapshotReadPort(
        items={
            DEFAULT_ITEM_ID: ItemSourceRecord(
                item_id=DEFAULT_ITEM_ID,
                item_name="ギフト",
                price=-1,
                item_url="https://example.com/items/item-001",
            ),
        },
    )

    with pytest.raises(ResultSnapshotBuilderError) as exc_info:
        build_result_snapshots(
            snapshot_input,
            item_reader=reader,
            item_repository=InMemoryRecommendationResultItemRepository(),
        )

    assert exc_info.value.error_code == ITEM_INFO_ERROR_CODE


# §14 No.11 INSERT 失敗
def test_build_snapshots_raises_grs_res_003_when_insert_fails() -> None:
    context = _sample_context()
    item_repository = InMemoryRecommendationResultItemRepository(
        should_fail_on_insert=True,
    )

    with pytest.raises(ResultSnapshotBuilderError) as exc_info:
        run_build_snapshots_from_context(context, item_repository=item_repository)

    assert exc_info.value.error_code == RESULT_ITEM_SAVE_ERROR_CODE


# §14 No.12 入力件数不整合
def test_build_snapshots_raises_grs_rec_012_when_items_length_mismatches_count() -> None:
    context = _sample_context()
    assert context.recommendation_result is not None
    context.recommendation_result.version_info["result_item_count"] = "2"

    with pytest.raises(ResultSnapshotBuilderError) as exc_info:
        run_build_snapshots_from_context(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
