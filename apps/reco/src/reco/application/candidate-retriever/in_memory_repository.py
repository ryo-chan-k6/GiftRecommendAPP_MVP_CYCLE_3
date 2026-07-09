"""In-memory Item Repository for MOD-RECO-012 MVP scaffold."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from reco.application.config_version_resolver import DEFAULT_EMBEDDING_MODEL_VERSION_ID

from .models import FilterPredicate, RetrievalCandidateItem
from .ports import ItemRepositoryPort


@dataclass(frozen=True)
class InMemoryItemRecord:
    """MVP in-memory item row for Filter / Vector 検索。"""

    item_id: str
    price: int | None
    is_active: bool
    active_status: str
    keywords: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    has_image: bool = True
    has_url: bool = True
    embedding: tuple[float, ...] | None = None
    model_version_id: str | None = None


@dataclass
class InMemoryItemRepository:
    """IF-DB-RECO-004 in-memory implementation for unit / smoke tests."""

    items: tuple[InMemoryItemRecord, ...] = ()
    search_calls: list[dict[str, object]] = field(default_factory=list)
    should_fail_search: bool = False

    def count_active_items(self) -> int:
        return sum(1 for item in self.items if item.is_active)

    def count_filtered_items(self, predicate: FilterPredicate) -> int:
        return sum(1 for item in self.items if _matches_predicate(item, predicate))

    def search_vector_candidates(
        self,
        predicate: FilterPredicate,
        *,
        query_vector: tuple[float, ...],
        model_version_id: str,
        limit: int,
    ) -> tuple[RetrievalCandidateItem, ...]:
        if self.should_fail_search:
            raise RuntimeError("simulated vector search failure")

        self.search_calls.append(
            {
                "predicate": predicate,
                "query_vector": query_vector,
                "model_version_id": model_version_id,
                "limit": limit,
            }
        )

        matched = [item for item in self.items if _matches_predicate(item, predicate)]
        scored: list[tuple[float, InMemoryItemRecord]] = []
        for item in matched:
            if item.embedding is None or item.model_version_id != model_version_id:
                continue
            score = _cosine_similarity(query_vector, item.embedding)
            scored.append((score, item))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return tuple(
            RetrievalCandidateItem(item_id=item.item_id, similarity_score=score)
            for score, item in scored[:limit]
        )


def _matches_predicate(item: InMemoryItemRecord, predicate: FilterPredicate) -> bool:
    if predicate.active_only:
        if not item.is_active or item.active_status != "active":
            return False

    merged = predicate.merged_filter_conditions
    if merged.budget_min is not None:
        if item.price is None or item.price < merged.budget_min:
            return False
    if merged.budget_max is not None:
        if item.price is None or item.price > merged.budget_max:
            return False

    for keyword in merged.ng_keywords:
        if _item_contains_keyword(item, keyword):
            return False
    for category in merged.ng_categories:
        if category in item.categories:
            return False

    rules = predicate.data_quality_rules
    if rules.get("require_image") and not item.has_image:
        return False
    if rules.get("require_url") and not item.has_url:
        return False

    return True


def _item_contains_keyword(item: InMemoryItemRecord, keyword: str) -> bool:
    lowered = keyword.lower()
    return any(lowered in existing.lower() for existing in item.keywords)


def _cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def build_default_in_memory_item_repository() -> InMemoryItemRepository:
    """Default in-memory catalog for scaffold / smoke tests."""
    dim = 4
    return InMemoryItemRepository(
        items=(
            InMemoryItemRecord(
                item_id="item-001",
                price=5000,
                is_active=True,
                active_status="active",
                keywords=("実用的",),
                categories=("gift",),
                embedding=(1.0, 0.0, 0.0, 0.0),
                model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION_ID,
            ),
            InMemoryItemRecord(
                item_id="item-002",
                price=8000,
                is_active=True,
                active_status="active",
                keywords=("カジュアル",),
                categories=("fashion",),
                embedding=(0.0, 1.0, 0.0, 0.0),
                model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION_ID,
            ),
            InMemoryItemRecord(
                item_id="item-003",
                price=12000,
                is_active=False,
                active_status="inactive",
                keywords=("高級",),
                categories=("gift",),
                embedding=(0.0, 0.0, 1.0, 0.0),
                model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION_ID,
            ),
        ),
    )


__all__ = [
    "InMemoryItemRecord",
    "InMemoryItemRepository",
    "ItemRepositoryPort",
    "build_default_in_memory_item_repository",
]
