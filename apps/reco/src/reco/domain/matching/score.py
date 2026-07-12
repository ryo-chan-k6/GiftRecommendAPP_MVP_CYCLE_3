"""Matching score placeholder."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatchingScore:
    """User–Item meaning alignment (Phase4a placeholder)."""

    item_id: str
    context_score: float | None = None
