"""Recommendation Request value object scaffold."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecommendationRequest:
    """User-facing recommendation input (Phase4a placeholder)."""

    request_id: str
    relationship: str | None = None
    occasion: str | None = None

    def has_gift_context(self) -> bool:
        """RQ-01: 推薦要求は最低限、贈答文脈または検索条件を持つ（骨格判定）。"""
        return self.relationship is not None or self.occasion is not None
