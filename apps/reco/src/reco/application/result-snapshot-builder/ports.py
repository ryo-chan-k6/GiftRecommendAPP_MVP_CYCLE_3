"""Repository ports for MOD-RECO-022."""

from __future__ import annotations

from typing import Protocol

from .models import (
    ItemPrimaryImageRecord,
    ItemReviewSnapshotRecord,
    ItemSourceRecord,
    RecommendationResultItemInsertRow,
)


class ItemSnapshotReadPort(Protocol):
    """Item / image / review 正本読取（§7.2）。"""

    def fetch_items(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemSourceRecord]:
        """item 行を item_id 一括 SELECT。"""
        ...

    def fetch_primary_images(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemPrimaryImageRecord]:
        """is_primary=true の主画像 URL を取得。"""
        ...

    def fetch_review_snapshots(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemReviewSnapshotRecord]:
        """item_review_summary を LEFT JOIN 相当で取得。"""
        ...


class RecommendationResultItemRepositoryPort(Protocol):
    """recommendation_result_item INSERT 境界。"""

    def insert_items(
        self,
        rows: tuple[RecommendationResultItemInsertRow, ...],
    ) -> int:
        """明細を一括 INSERT し、挿入件数を返す。"""
        ...
