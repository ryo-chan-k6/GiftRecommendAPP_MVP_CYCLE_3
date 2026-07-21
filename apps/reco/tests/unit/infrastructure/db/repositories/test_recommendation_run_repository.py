"""In-memory RecommendationRunRepository unit tests (MOD-RECO-002 scaffold)."""

from __future__ import annotations

import pytest

from reco.domain.recommendation.run import RunStatus
from reco.infrastructure.db.repositories.recommendation_run_repository import (
    InMemoryRecommendationRunRepository,
)


def test_insert_accepted_creates_row_with_accepted_status() -> None:
    repository = InMemoryRecommendationRunRepository()

    record = repository.insert_accepted(
        request_id="req-1",
        pair_id="pair-1",
        semantic_config_version_id="scv-1",
        model_version_id="mv-1",
        matching_config_id="mc-1",
        ranking_config_id="rc-1",
    )

    assert record.run_id
    assert record.run_status is RunStatus.ACCEPTED
    assert record.started_at is None
    assert record.completed_at is None
    assert repository.get_by_id(record.run_id) == record


def test_update_status_persists_timestamps() -> None:
    repository = InMemoryRecommendationRunRepository()
    accepted = repository.insert_accepted(
        request_id="req-1",
        pair_id="pair-1",
        semantic_config_version_id="scv-1",
        model_version_id="mv-1",
        matching_config_id="mc-1",
        ranking_config_id="rc-1",
    )

    running = repository.update_status(
        accepted.run_id,
        run_status=RunStatus.RUNNING,
        started_at=accepted.created_at,
    )
    succeeded = repository.update_status(
        accepted.run_id,
        run_status=RunStatus.SUCCEEDED,
        started_at=running.started_at,
        completed_at=running.updated_at,
    )

    assert succeeded.run_status is RunStatus.SUCCEEDED
    assert succeeded.started_at is not None
    assert succeeded.completed_at is not None


def test_request_exists_honors_known_request_ids() -> None:
    repository = InMemoryRecommendationRunRepository(
        known_request_ids={"req-known"},
    )

    assert repository.request_exists("req-known") is True
    assert repository.request_exists("req-unknown") is False


def test_version_exists_honors_known_version_ids() -> None:
    repository = InMemoryRecommendationRunRepository(
        known_version_ids={"scv-1", "mv-1", "mc-1", "rc-1"},
    )

    assert (
        repository.version_exists(
            semantic_config_version_id="scv-1",
            model_version_id="mv-1",
            matching_config_id="mc-1",
            ranking_config_id="rc-1",
        )
        is True
    )
    assert (
        repository.version_exists(
            semantic_config_version_id="scv-missing",
            model_version_id="mv-1",
            matching_config_id="mc-1",
            ranking_config_id="rc-1",
        )
        is False
    )


def test_insert_raises_when_write_failure_configured() -> None:
    repository = InMemoryRecommendationRunRepository(should_fail_on_write=True)

    with pytest.raises(RuntimeError, match="insert failed"):
        repository.insert_accepted(
            request_id="req-1",
            pair_id="pair-1",
            semantic_config_version_id="scv-1",
            model_version_id="mv-1",
            matching_config_id="mc-1",
            ranking_config_id="rc-1",
        )
