"""Recommendation Result value object scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReasonStatus(StrEnum):
    """Reason generation state for a result item."""

    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ResultStatus(StrEnum):
    """Overall recommendation result status."""

    COMPLETED = "completed"
    PARTIAL = "partial"
    EMPTY = "empty"


@dataclass(frozen=True)
class RecommendationResultItem:
    """Single ranked item in a recommendation result."""

    item_id: str
    rank: int
    final_score: float | None = None
    reason_summary: str | None = None
    reason_status: ReasonStatus | None = None
    reason_detail: str | None = None
    reason_points: tuple[str, ...] | None = None
    is_fallback: bool = False


@dataclass(frozen=True)
class RecommendationResult:
    """Output collection for a completed recommendation run."""

    run_id: str
    request_id: str | None = None
    items: tuple[RecommendationResultItem, ...] = ()
    result_status: ResultStatus = ResultStatus.COMPLETED
    version_info: dict[str, str] | None = None

    @property
    def item_count(self) -> int:
        return len(self.items)
