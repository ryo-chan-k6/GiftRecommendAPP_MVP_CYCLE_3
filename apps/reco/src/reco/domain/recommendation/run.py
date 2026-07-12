"""Recommendation Run entity scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RunStatus(StrEnum):
    """Execution lifecycle for a single recommendation run (DB enum aligned)."""

    ACCEPTED = "accepted"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass(frozen=True)
class RecommendationRun:
    """Single recommendation execution unit (Phase4a placeholder)."""

    run_id: str
    request_id: str
    status: RunStatus = RunStatus.ACCEPTED
    semantic_config_version: str | None = None
    model_version: str | None = None

    def with_status(self, status: RunStatus) -> RecommendationRun:
        return RecommendationRun(
            run_id=self.run_id,
            request_id=self.request_id,
            status=status,
            semantic_config_version=self.semantic_config_version,
            model_version=self.model_version,
        )
