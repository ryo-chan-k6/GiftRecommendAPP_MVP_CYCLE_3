"""Ports for MOD-RECO-013 (IF-DB-RECO-004 Item Repository boundary)."""

from __future__ import annotations

from typing import Protocol

from .models import ItemSemanticRecord, ItemValidationRecord


class ItemRepositoryPort(Protocol):
    """item / item_semantic / item_image 参照（IF-DB-RECO-004）。"""

    def fetch_items_for_validation(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemValidationRecord]:
        """候補 item_id 集合に対する item / item_image 参照。"""
        ...

    def fetch_item_semantics(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemSemanticRecord]:
        """候補 item の item_semantic 参照。"""
        ...
