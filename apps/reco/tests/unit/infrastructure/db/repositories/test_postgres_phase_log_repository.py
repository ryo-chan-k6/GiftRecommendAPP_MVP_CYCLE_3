"""Postgres PhaseLogRepository unit tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from reco.application.phase_log_writer.models import PhaseLogRecord
from reco.infrastructure.db.repositories.postgres_phase_log_repository import (
    PostgresPhaseLogRepository,
)
from unit.infrastructure.db.helpers import ScriptedDatabaseSession


def _started_record() -> PhaseLogRecord:
    return PhaseLogRecord(
        trace_id="trace-1",
        owner_type="recommendation_run",
        owner_id=str(uuid4()),
        phase_name="retrieval_completed",
        phase_status="started",
        started_at=datetime.now(UTC),
        detail_json={"module_id": "MOD-RECO-012"},
    )


def test_insert_started_returns_phase_log_id() -> None:
    phase_log_id = str(uuid4())
    session = ScriptedDatabaseSession(
        scripted_query_results=[[{"phase_log_id": phase_log_id}]]
    )
    repository = PostgresPhaseLogRepository(session=session)

    assert repository.insert_started(_started_record()) == phase_log_id
    assert "INSERT INTO phase_log" in session.operations[0][1]


def test_update_terminal_raises_when_row_missing() -> None:
    session = ScriptedDatabaseSession(scripted_query_results=[[], []])
    repository = PostgresPhaseLogRepository(session=session)
    phase_log_id = str(uuid4())

    with pytest.raises(KeyError, match="not found"):
        repository.update_terminal(
            phase_log_id,
            phase_status="succeeded",
            completed_at=datetime.now(UTC),
            duration_ms=10,
            error_code=None,
            detail_json={},
        )


def test_update_terminal_raises_when_status_not_started() -> None:
    phase_log_id = str(uuid4())
    session = ScriptedDatabaseSession(
        scripted_query_results=[[], [{"phase_status": "succeeded"}]]
    )
    repository = PostgresPhaseLogRepository(session=session)

    with pytest.raises(ValueError, match="requires started status"):
        repository.update_terminal(
            phase_log_id,
            phase_status="failed",
            completed_at=datetime.now(UTC),
            duration_ms=10,
            error_code="GRS-REC-002",
            detail_json={"error": True},
        )
