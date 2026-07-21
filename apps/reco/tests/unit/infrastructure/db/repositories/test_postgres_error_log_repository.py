"""Postgres ErrorLogRepository unit tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from reco.application.error_log_writer.models import ErrorLogRecord
from reco.infrastructure.db.repositories.postgres_error_log_repository import (
    PostgresErrorLogRepository,
)
from unit.infrastructure.db.helpers import ScriptedDatabaseSession


def test_insert_returns_error_log_id() -> None:
    error_log_id = str(uuid4())
    session = ScriptedDatabaseSession(
        scripted_query_results=[[{"error_log_id": error_log_id}]]
    )
    repository = PostgresErrorLogRepository(session=session)

    record = ErrorLogRecord(
        trace_id="trace-1",
        request_id="req-1",
        owner_type="recommendation_run",
        owner_id=str(uuid4()),
        service="reco",
        error_code="GRS-REC-002",
        error_message="insert failed",
        severity="error",
        retryable=False,
        error_detail_json={"module_id": "MOD-RECO-002"},
        occurred_at=datetime.now(UTC),
    )

    assert repository.insert(record) == error_log_id
    assert "INSERT INTO error_log" in session.operations[0][1]
