"""Recommendation Result value object scaffold."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecommendationResultItem:
    """Single ranked item in a recommendation result."""

    item_id: str
    rank: int
    final_score: float | None = None


@dataclass(frozen=True)
class RecommendationResult:
    """Output collection for a completed recommendation run."""

    run_id: str
    items: tuple[RecommendationResultItem, ...] = ()

    @property
    def item_count(self) -> int:
        return len(self.items)
