"""In-memory repositories for MOD-RECO-022 MVP scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field

from reco.application.popularity_scorer.models import ItemReviewSummary

from .models import (
    ItemPrimaryImageRecord,
    ItemReviewSnapshotRecord,
    ItemSourceRecord,
    RecommendationResultItemInsertRow,
)
from .ports import ItemSnapshotReadPort, RecommendationResultItemRepositoryPort


@dataclass(frozen=True)
class InMemoryItemSnapshotSource:
    """MVP in-memory item + image + review row."""

    item_id: str
    item_name: str
    price: int
    item_url: str
    catchcopy: str | None = None
    shop_code: str | None = None
    primary_image_url: str | None = None
    review_summary: ItemReviewSummary | None = None


@dataclass
class InMemoryItemSnapshotReadRepository:
    """ItemSnapshotReadPort in-memory implementation."""

    items: dict[str, InMemoryItemSnapshotSource] = field(default_factory=dict)
    should_fail_on_fetch: bool = False

    def register_item(self, source: InMemoryItemSnapshotSource) -> None:
        self.items[source.item_id] = source

    def fetch_items(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemSourceRecord]:
        if self.should_fail_on_fetch:
            raise RuntimeError("simulated item fetch failure")

        result: dict[str, ItemSourceRecord] = {}
        for item_id in item_ids:
            source = self.items.get(item_id)
            if source is None:
                continue
            result[item_id] = ItemSourceRecord(
                item_id=source.item_id,
                item_name=source.item_name,
                price=source.price,
                item_url=source.item_url,
                catchcopy=source.catchcopy,
                shop_code=source.shop_code,
            )
        return result

    def fetch_primary_images(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemPrimaryImageRecord]:
        if self.should_fail_on_fetch:
            raise RuntimeError("simulated item image fetch failure")

        result: dict[str, ItemPrimaryImageRecord] = {}
        for item_id in item_ids:
            source = self.items.get(item_id)
            if source is None or source.primary_image_url is None:
                continue
            result[item_id] = ItemPrimaryImageRecord(
                item_id=item_id,
                image_url=source.primary_image_url,
            )
        return result

    def fetch_review_snapshots(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemReviewSnapshotRecord]:
        if self.should_fail_on_fetch:
            raise RuntimeError("simulated review fetch failure")

        result: dict[str, ItemReviewSnapshotRecord] = {}
        for item_id in item_ids:
            source = self.items.get(item_id)
            if source is None or source.review_summary is None:
                continue
            result[item_id] = ItemReviewSnapshotRecord(
                item_id=item_id,
                review_average=source.review_summary.review_average,
                review_count=source.review_summary.review_count,
            )
        return result


@dataclass
class InMemoryRecommendationResultItemRepository:
    """recommendation_result_item INSERT の in-memory 実装。"""

    rows_by_result_id: dict[str, tuple[RecommendationResultItemInsertRow, ...]] = field(
        default_factory=dict,
    )
    should_fail_on_insert: bool = False

    def insert_items(
        self,
        rows: tuple[RecommendationResultItemInsertRow, ...],
    ) -> int:
        if self.should_fail_on_insert:
            raise RuntimeError("recommendation_result_item insert failed")

        if not rows:
            return 0

        recommendation_result_id = rows[0].recommendation_result_id
        if recommendation_result_id in self.rows_by_result_id:
            raise RuntimeError(
                f"duplicate recommendation_result_item insert: {recommendation_result_id}",
            )

        self.rows_by_result_id[recommendation_result_id] = rows
        return len(rows)


def build_default_in_memory_item_snapshot_read_repository() -> (
    InMemoryItemSnapshotReadRepository
):
    repo = InMemoryItemSnapshotReadRepository()
    repo.register_item(
        InMemoryItemSnapshotSource(
            item_id="item-001",
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


__all__ = [
    "InMemoryItemSnapshotReadRepository",
    "InMemoryItemSnapshotSource",
    "InMemoryRecommendationResultItemRepository",
    "build_default_in_memory_item_snapshot_read_repository",
]
