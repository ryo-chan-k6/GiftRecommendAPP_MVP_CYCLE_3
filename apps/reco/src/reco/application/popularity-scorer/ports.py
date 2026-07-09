"""Ports for MOD-RECO-017 (item_review_summary Repository boundary)."""

from __future__ import annotations

from typing import Protocol

from .models import ItemReviewSummary


class ItemReviewSummaryRepositoryPort(Protocol):
    """item_review_summary 参照（候補 item_id 一括 SELECT）。"""

    def fetch_review_summaries(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemReviewSummary]:
        """候補 item_id 集合に対するレビュー集計。行不在 item は dict に含めない。"""
        ...
