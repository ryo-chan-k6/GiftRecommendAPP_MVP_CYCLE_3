"""Recommendation Run persistence (IF-DB-RECO-002)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from reco.domain.recommendation.run import RunStatus


@dataclass(frozen=True)
class RecommendationRunRecord:
    """Persisted recommendation_run row snapshot."""

    run_id: str
    request_id: str
    pair_id: str
    semantic_config_version_id: str
    model_version_id: str
    matching_config_id: str
    ranking_config_id: str
    run_status: RunStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class RecommendationRunRepository(Protocol):
    """Persistence boundary for recommendation_run."""

    def request_exists(self, request_id: str) -> bool: ...

    def version_exists(
        self,
        *,
        semantic_config_version_id: str,
        model_version_id: str,
        matching_config_id: str,
        ranking_config_id: str,
    ) -> bool: ...

    def insert_accepted(
        self,
        *,
        request_id: str,
        pair_id: str,
        semantic_config_version_id: str,
        model_version_id: str,
        matching_config_id: str,
        ranking_config_id: str,
    ) -> RecommendationRunRecord: ...

    def get_by_id(self, run_id: str) -> RecommendationRunRecord | None: ...

    def update_status(
        self,
        run_id: str,
        *,
        run_status: RunStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> RecommendationRunRecord: ...


@dataclass
class InMemoryRecommendationRunRepository:
    """Phase4a in-memory repository for unit tests and scaffold wiring."""

    known_request_ids: set[str] = field(default_factory=set)
    known_version_ids: set[str] = field(default_factory=set)
    runs: dict[str, RecommendationRunRecord] = field(default_factory=dict)
    should_fail_on_write: bool = False

    def request_exists(self, request_id: str) -> bool:
        if not self.known_request_ids:
            return True
        return request_id in self.known_request_ids

    def version_exists(
        self,
        *,
        semantic_config_version_id: str,
        model_version_id: str,
        matching_config_id: str,
        ranking_config_id: str,
    ) -> bool:
        if not self.known_version_ids:
            return True
        return (
            semantic_config_version_id in self.known_version_ids
            and model_version_id in self.known_version_ids
            and matching_config_id in self.known_version_ids
            and ranking_config_id in self.known_version_ids
        )

    def insert_accepted(
        self,
        *,
        request_id: str,
        pair_id: str,
        semantic_config_version_id: str,
        model_version_id: str,
        matching_config_id: str,
        ranking_config_id: str,
    ) -> RecommendationRunRecord:
        if self.should_fail_on_write:
            raise RuntimeError("insert failed")

        now = datetime.now(UTC)
        record = RecommendationRunRecord(
            run_id=str(uuid4()),
            request_id=request_id,
            pair_id=pair_id,
            semantic_config_version_id=semantic_config_version_id,
            model_version_id=model_version_id,
            matching_config_id=matching_config_id,
            ranking_config_id=ranking_config_id,
            run_status=RunStatus.ACCEPTED,
            created_at=now,
            updated_at=now,
        )
        self.runs[record.run_id] = record
        return record

    def get_by_id(self, run_id: str) -> RecommendationRunRecord | None:
        return self.runs.get(run_id)

    def update_status(
        self,
        run_id: str,
        *,
        run_status: RunStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> RecommendationRunRecord:
        if self.should_fail_on_write:
            raise RuntimeError("update failed")

        current = self.runs.get(run_id)
        if current is None:
            raise KeyError(f"recommendation_run not found: {run_id}")

        now = datetime.now(UTC)
        updated = RecommendationRunRecord(
            run_id=current.run_id,
            request_id=current.request_id,
            pair_id=current.pair_id,
            semantic_config_version_id=current.semantic_config_version_id,
            model_version_id=current.model_version_id,
            matching_config_id=current.matching_config_id,
            ranking_config_id=current.ranking_config_id,
            run_status=run_status,
            started_at=started_at if started_at is not None else current.started_at,
            completed_at=(
                completed_at if completed_at is not None else current.completed_at
            ),
            created_at=current.created_at,
            updated_at=now,
        )
        self.runs[run_id] = updated
        return updated
