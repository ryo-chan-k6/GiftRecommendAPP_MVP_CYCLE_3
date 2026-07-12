"""Ports for MOD-RECO-012 (IF-DB-RECO-004 Item Repository boundary)."""

from __future__ import annotations

from typing import Protocol

from .models import FilterPredicate, RetrievalCandidateItem


class ItemRepositoryPort(Protocol):
    """Item 参照・Filter 件数集計・Vector 検索（IF-DB-RECO-004）。"""

    def count_active_items(self) -> int:
        """Filter 前の有効 item 件数（active_item_filter 適用前の母集団）。"""
        ...

    def count_filtered_items(self, predicate: FilterPredicate) -> int:
        """filter_predicate 適用後の件数。"""
        ...

    def search_vector_candidates(
        self,
        predicate: FilterPredicate,
        *,
        query_vector: tuple[float, ...],
        model_version_id: str,
        limit: int,
    ) -> tuple[RetrievalCandidateItem, ...]:
        """predicate 適用下で Vector 類似度検索。"""
        ...
