"""Unit tests for PostgresRunValidation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from reco.domain.recommendation.run import RunStatus
from reco.infrastructure.db.repositories.postgres_run_validation import (
    PostgresRunValidation,
)
from reco.infrastructure.db.repositories.recommendation_run_repository import (
    RecommendationRunRecord,
)


@dataclass
class _FakeRunRepository:
    records: dict[str, RecommendationRunRecord]

    def get_by_id(self, run_id: str) -> RecommendationRunRecord | None:
        return self.records.get(run_id)


def _sample_record(run_id: str, semantic_version: str) -> RecommendationRunRecord:
    now = datetime.now(UTC)
    return RecommendationRunRecord(
        run_id=run_id,
        request_id="req-1",
        pair_id="pair-1",
        semantic_config_version_id=semantic_version,
        model_version_id="model-1",
        matching_config_id="matching-1",
        ranking_config_id="ranking-1",
        run_status=RunStatus.RUNNING,
        started_at=now,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )


def test_postgres_run_validation_returns_semantic_config_version_id() -> None:
    run_id = "11111111-1111-4111-8111-111111111111"
    semantic = "22222222-2222-4222-8222-222222222222"
    validation = PostgresRunValidation(
        run_repository=_FakeRunRepository(  # type: ignore[arg-type]
            {_sample_record(run_id, semantic).run_id: _sample_record(run_id, semantic)},
        ),
    )

    assert validation.get_semantic_config_version_id(run_id) == semantic


def test_postgres_run_validation_returns_embedding_model_version_id() -> None:
    run_id = "11111111-1111-4111-8111-111111111111"
    semantic = "22222222-2222-4222-8222-222222222222"
    record = _sample_record(run_id, semantic)
    validation = PostgresRunValidation(
        run_repository=_FakeRunRepository(  # type: ignore[arg-type]
            {record.run_id: record},
        ),
    )
    assert validation.get_embedding_model_version_id(run_id) == record.model_version_id


def test_postgres_run_validation_returns_none_when_missing() -> None:
    validation = PostgresRunValidation(
        run_repository=_FakeRunRepository({}),  # type: ignore[arg-type]
    )
    assert validation.get_semantic_config_version_id("missing") is None
    assert validation.get_embedding_model_version_id("missing") is None
