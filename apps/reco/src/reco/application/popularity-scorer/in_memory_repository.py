"""In-memory item_review_summary repository for unit tests and scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import ItemReviewSummary
from .ports import ItemReviewSummaryRepositoryPort


@dataclass
class InMemoryItemReviewSummaryRepository:
    """item_review_summary 参照の in-memory 実装。"""

    records: dict[str, ItemReviewSummary] = field(default_factory=dict)
    should_fail_on_fetch: bool = False

    def register_review_summary(
        self,
        item_id: str,
        summary: ItemReviewSummary,
    ) -> None:
        self.records[item_id] = summary

    def fetch_review_summaries(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemReviewSummary]:
        if self.should_fail_on_fetch:
            raise RuntimeError("item_review_summary fetch failed")

        return {
            item_id: self.records[item_id]
            for item_id in item_ids
            if item_id in self.records
        }


def build_default_in_memory_item_review_summary_repository() -> (
    InMemoryItemReviewSummaryRepository
):
    repo = InMemoryItemReviewSummaryRepository()
    repo.register_review_summary(
        "item-001",
        ItemReviewSummary(review_average=4.0, review_count=120),
    )
    return repo


__all__ = [
    "InMemoryItemReviewSummaryRepository",
    "build_default_in_memory_item_review_summary_repository",
]
