"""Repository ports for MOD-RECO-021."""

from __future__ import annotations

from typing import Protocol

from .models import RecommendationResultHeaderInsertRow


class RecommendationResultRepositoryPort(Protocol):
    """Persistence boundary for ``recommendation_result`` header INSERT."""

    def insert_header(
        self,
        row: RecommendationResultHeaderInsertRow,
    ) -> RecommendationResultHeaderInsertRow: ...
