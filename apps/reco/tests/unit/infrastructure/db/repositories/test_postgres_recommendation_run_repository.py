"""Postgres RecommendationRunRepository unit tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from reco.domain.recommendation.run import RunStatus
from reco.infrastructure.db.repositories.postgres_recommendation_run_repository import (
    PostgresRecommendationRunRepository,
)
from unit.infrastructure.db.helpers import ScriptedDatabaseSession


def _sample_row(**overrides: object) -> dict[str, object]:
    now = datetime.now(UTC)
    row = {
        "recommendation_run_id": str(uuid4()),
        "recommendation_request_id": str(uuid4()),
        "pair_id": str(uuid4()),
        "semantic_config_version_id": str(uuid4()),
        "model_version_id": str(uuid4()),
        "matching_config_id": str(uuid4()),
        "ranking_config_id": str(uuid4()),
        "run_status": RunStatus.ACCEPTED.value,
        "started_at": None,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
    }
    row.update(overrides)
    return row


def test_request_exists_queries_recommendation_request() -> None:
    session = ScriptedDatabaseSession(scripted_query_results=[[{"found": 1}]])
    repository = PostgresRecommendationRunRepository(session=session)

    assert repository.request_exists("req-1") is True
    assert session.operations[0][0] == "query"
    assert "recommendation_request" in session.operations[0][1]


def test_version_exists_requires_all_versions() -> None:
    session = ScriptedDatabaseSession(
        scripted_query_results=[
            [
                {
                    "semantic_exists": True,
                    "model_exists": True,
                    "matching_exists": True,
                    "ranking_exists": False,
                }
            ]
        ]
    )
    repository = PostgresRecommendationRunRepository(session=session)

    assert (
        repository.version_exists(
            semantic_config_version_id="scv",
            model_version_id="mv",
            matching_config_id="mc",
            ranking_config_id="rc",
        )
        is False
    )


def test_insert_accepted_maps_returned_row() -> None:
    row = _sample_row()
    session = ScriptedDatabaseSession(scripted_query_results=[[row]])
    repository = PostgresRecommendationRunRepository(session=session)

    record = repository.insert_accepted(
        request_id=str(row["recommendation_request_id"]),
        pair_id=str(row["pair_id"]),
        semantic_config_version_id=str(row["semantic_config_version_id"]),
        model_version_id=str(row["model_version_id"]),
        matching_config_id=str(row["matching_config_id"]),
        ranking_config_id=str(row["ranking_config_id"]),
    )

    assert record.run_id == row["recommendation_run_id"]
    assert record.run_status is RunStatus.ACCEPTED


def test_update_status_raises_when_run_missing() -> None:
    session = ScriptedDatabaseSession()
    repository = PostgresRecommendationRunRepository(session=session)

    with pytest.raises(KeyError, match="not found"):
        repository.update_status(str(uuid4()), run_status=RunStatus.RUNNING)


def test_update_status_uses_existing_timestamps_when_omitted() -> None:
    started = datetime.now(UTC)
    row = _sample_row(started_at=started, run_status=RunStatus.RUNNING.value)
    updated = _sample_row(
        recommendation_run_id=row["recommendation_run_id"],
        recommendation_request_id=row["recommendation_request_id"],
        pair_id=row["pair_id"],
        semantic_config_version_id=row["semantic_config_version_id"],
        model_version_id=row["model_version_id"],
        matching_config_id=row["matching_config_id"],
        ranking_config_id=row["ranking_config_id"],
        started_at=started,
        completed_at=started,
        run_status=RunStatus.SUCCEEDED.value,
    )
    session = ScriptedDatabaseSession(
        scripted_query_results=[[row], [updated]],
    )
    repository = PostgresRecommendationRunRepository(session=session)

    record = repository.update_status(
        str(row["recommendation_run_id"]),
        run_status=RunStatus.SUCCEEDED,
        completed_at=started,
    )

    assert record.run_status is RunStatus.SUCCEEDED
    assert record.started_at == started