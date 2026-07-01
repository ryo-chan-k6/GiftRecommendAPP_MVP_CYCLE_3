"""In-memory Item Repository for MOD-RECO-013 MVP scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field

from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID

from .models import ItemSemanticConcept, ItemSemanticRecord, ItemValidationRecord
from .ports import ItemRepositoryPort


@dataclass(frozen=True)
class InMemoryItemRecord:
    """MVP in-memory item + semantic row for Post Hard Filter."""

    item_id: str
    name: str | None
    price: int | None
    is_active: bool
    active_status: str
    has_image: bool = True
    semantic_config_version_id: str = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    semantic_concepts: tuple[ItemSemanticConcept, ...] = ()


@dataclass
class InMemoryItemRepository:
    """IF-DB-RECO-004 in-memory implementation for unit / smoke tests."""

    items: dict[str, InMemoryItemRecord] = field(default_factory=dict)
    should_fail_fetch: bool = False

    def fetch_items_for_validation(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemValidationRecord]:
        if self.should_fail_fetch:
            raise RuntimeError("simulated item fetch failure")

        result: dict[str, ItemValidationRecord] = {}
        for item_id in item_ids:
            record = self.items.get(item_id)
            if record is None:
                continue
            result[item_id] = ItemValidationRecord(
                item_id=record.item_id,
                name=record.name,
                price=record.price,
                is_active=record.is_active,
                active_status=record.active_status,
                has_image=record.has_image,
            )
        return result

    def fetch_item_semantics(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemSemanticRecord]:
        if self.should_fail_fetch:
            raise RuntimeError("simulated item_semantic fetch failure")

        result: dict[str, ItemSemanticRecord] = {}
        for item_id in item_ids:
            record = self.items.get(item_id)
            if record is None:
                continue
            result[item_id] = ItemSemanticRecord(
                item_id=record.item_id,
                semantic_config_version_id=record.semantic_config_version_id,
                concepts=record.semantic_concepts,
            )
        return result


def build_default_in_memory_item_repository() -> InMemoryItemRepository:
    """Default in-memory catalog for scaffold / smoke tests."""
    return InMemoryItemRepository(
        items={
            "item-001": InMemoryItemRecord(
                item_id="item-001",
                name="実用的ギフト",
                price=5000,
                is_active=True,
                active_status="active",
                semantic_concepts=(
                    ItemSemanticConcept(concept_code="practical", confidence=0.9),
                ),
            ),
            "item-002": InMemoryItemRecord(
                item_id="item-002",
                name="カジュアル雑貨",
                price=8000,
                is_active=True,
                active_status="active",
                semantic_concepts=(
                    ItemSemanticConcept(concept_code="casual", confidence=0.85),
                ),
            ),
        },
    )


__all__ = [
    "InMemoryItemRecord",
    "InMemoryItemRepository",
    "ItemRepositoryPort",
    "build_default_in_memory_item_repository",
]
