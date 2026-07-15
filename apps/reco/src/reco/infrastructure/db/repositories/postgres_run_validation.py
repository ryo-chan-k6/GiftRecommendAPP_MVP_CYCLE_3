"""Postgres-backed RunValidation for early reco pipeline modules."""

from __future__ import annotations

from dataclasses import dataclass

from reco.infrastructure.db.repositories.postgres_recommendation_run_repository import (
    PostgresRecommendationRunRepository,
)


@dataclass(frozen=True)
class PostgresRunValidation:
    """Resolve semantic_config_version_id from recommendation_run (Postgres).

    Used by production composition for modules that previously relied on
    InMemoryRunValidation (empty unless a test registered the run).
    """

    run_repository: PostgresRecommendationRunRepository

    def get_semantic_config_version_id(self, recommendation_run_id: str) -> str | None:
        record = self.run_repository.get_by_id(recommendation_run_id)
        if record is None:
            return None
        return record.semantic_config_version_id
