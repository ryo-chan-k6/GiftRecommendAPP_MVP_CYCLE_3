"""In-memory recommendation_result header repository for tests and scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import RecommendationResultHeaderInsertRow


@dataclass
class InMemoryRecommendationResultRepository:
    """Phase4a in-memory repository enforcing ``uq_result_per_run``."""

    headers_by_run_id: dict[str, RecommendationResultHeaderInsertRow] = field(
        default_factory=dict,
    )
    should_fail_on_insert: bool = False

    def insert_header(
        self,
        row: RecommendationResultHeaderInsertRow,
    ) -> RecommendationResultHeaderInsertRow:
        if self.should_fail_on_insert:
            raise RuntimeError("recommendation_result insert failed")

        if row.recommendation_run_id in self.headers_by_run_id:
            raise RuntimeError(
                f"duplicate recommendation_result for run: {row.recommendation_run_id}",
            )

        self.headers_by_run_id[row.recommendation_run_id] = row
        return row
