"""Unit tests for phase_log / error_log writers (E4 Wave 2)."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from batch.application.genre_sync.repositories import GenreSyncRepositories
from batch.application.observability import (
    ALLOWED_BATCH_PHASE_NAMES,
    PostgresApiCallLogWriter,
    PostgresErrorLogWriter,
    PostgresPhaseLogWriter,
    ScaffoldErrorLogWriter,
    ScaffoldPhaseLogWriter,
    create_batch_observability_writers,
    create_error_log_writer,
    create_phase_log_writer,
    map_app_phase_status,
    map_app_phase_to_ddl,
)
from batch.infrastructure.db import ScaffoldDbWriter
from batch.infrastructure.object_storage import ScaffoldObjectStorageClient


def test_postgres_phase_rejects_non_uuid() -> None:
    writer = ScaffoldDbWriter()
    phase_writer = PostgresPhaseLogWriter(db_writer=writer)

    with pytest.raises(ValueError, match="batch_run_id must be a UUID"):
        phase_writer.record_phase(
            batch_run_id="not-a-uuid",
            phase_name="batch_started",
            phase_status="succeeded",
        )


def test_postgres_phase_rejects_invalid_phase_name() -> None:
    writer = ScaffoldDbWriter()
    phase_writer = PostgresPhaseLogWriter(db_writer=writer)
    run_id = str(uuid4())

    with pytest.raises(ValueError, match="not allowed for owner_type=batch_run"):
        phase_writer.record_phase(
            batch_run_id=run_id,
            phase_name="plan",
            phase_status="succeeded",
        )
    assert "plan" not in ALLOWED_BATCH_PHASE_NAMES


def test_postgres_phase_writes_expected_columns() -> None:
    writer = ScaffoldDbWriter()
    phase_writer = PostgresPhaseLogWriter(db_writer=writer)
    run_id = str(uuid4())

    phase_writer.record_phase(
        batch_run_id=run_id,
        phase_name="batch_started",
        phase_status="succeeded",
        app_phase="plan",
        trace_id="trace-1",
    )

    assert len(writer.write_calls) == 1
    call = writer.write_calls[0]
    assert call["table"] == "phase_log"
    row = call["rows"][0]
    assert row["owner_type"] == "batch_run"
    assert row["owner_id"] == run_id
    assert row["phase_name"] == "batch_started"
    assert row["phase_status"] == "succeeded"
    assert row["trace_id"] == "trace-1"
    assert isinstance(row["started_at"], datetime)
    assert row["started_at"].tzinfo is not None
    assert isinstance(row["completed_at"], datetime)
    assert row["duration_ms"] == 0
    detail = row["detail_json"]
    # Scaffold / Json wrapper both expose app_phase
    if hasattr(detail, "obj"):
        detail = detail.obj
    assert detail["app_phase"] == "plan"
    assert len(phase_writer.records) == 1


def test_postgres_phase_started_has_null_completed_at() -> None:
    writer = ScaffoldDbWriter()
    phase_writer = PostgresPhaseLogWriter(db_writer=writer)
    run_id = str(uuid4())

    phase_writer.record_phase(
        batch_run_id=run_id,
        phase_name="batch_started",
        phase_status="started",
    )

    row = writer.write_calls[0]["rows"][0]
    assert row["completed_at"] is None
    assert row["duration_ms"] is None


def test_postgres_error_rejects_non_uuid() -> None:
    writer = ScaffoldDbWriter()
    error_writer = PostgresErrorLogWriter(db_writer=writer)

    with pytest.raises(ValueError, match="batch_run_id must be a UUID"):
        error_writer.record_error(
            batch_run_id="local-run",
            error_code="GRS-BAT-001",
            error_message="boom",
        )


def test_postgres_error_rejects_invalid_error_code() -> None:
    writer = ScaffoldDbWriter()
    error_writer = PostgresErrorLogWriter(db_writer=writer)
    run_id = str(uuid4())

    with pytest.raises(ValueError, match="error_code must match"):
        error_writer.record_error(
            batch_run_id=run_id,
            error_code="INVALID",
            error_message="boom",
        )


def test_postgres_error_writes_expected_columns() -> None:
    writer = ScaffoldDbWriter()
    error_writer = PostgresErrorLogWriter(db_writer=writer)
    run_id = str(uuid4())

    error_writer.record_error(
        batch_run_id=run_id,
        error_code="GRS-BAT-001",
        error_message="empty fetch_plan",
        detail={"genre_id": "0"},
        trace_id="trace-err",
    )

    assert len(writer.write_calls) == 1
    call = writer.write_calls[0]
    assert call["table"] == "error_log"
    row = call["rows"][0]
    assert row["owner_type"] == "batch_run"
    assert row["owner_id"] == run_id
    assert row["service"] == "batch"
    assert row["error_code"] == "GRS-BAT-001"
    assert row["error_message"] == "empty fetch_plan"
    assert row["severity"] == "error"
    assert row["retryable"] is False
    assert row["trace_id"] == "trace-err"
    assert isinstance(row["occurred_at"], datetime)
    assert row["occurred_at"].tzinfo is not None
    detail = row["error_detail_json"]
    if hasattr(detail, "obj"):
        detail = detail.obj
    assert detail == {"genre_id": "0"}
    assert len(error_writer.records) == 1


def test_postgres_error_strips_sensitive_detail_keys() -> None:
    writer = ScaffoldDbWriter()
    error_writer = PostgresErrorLogWriter(db_writer=writer)
    run_id = str(uuid4())

    error_writer.record_error(
        batch_run_id=run_id,
        error_code="GRS-BAT-001",
        error_message="leak attempt",
        detail={
            "genre_id": "100",
            "Authorization": "Bearer secret",
            "url": "https://example.invalid",
            "access_key": "AKIA...",
        },
    )

    detail = writer.write_calls[0]["rows"][0]["error_detail_json"]
    if hasattr(detail, "obj"):
        detail = detail.obj
    assert detail == {"genre_id": "100"}
    assert "Authorization" not in detail
    assert "url" not in detail
    assert "access_key" not in detail


def test_scaffold_writers_record_in_memory() -> None:
    phase = ScaffoldPhaseLogWriter()
    error = ScaffoldErrorLogWriter()
    phase.record_phase(
        batch_run_id="job-1",
        phase_name="batch_started",
        phase_status="succeeded",
        app_phase="plan",
    )
    error.record_error(
        batch_run_id="job-1",
        error_code="GRS-BAT-001",
        error_message="x",
    )
    assert len(phase.records) == 1
    assert len(error.records) == 1


def test_create_phase_log_writer_scaffold_demo() -> None:
    assert isinstance(
        create_phase_log_writer(scaffold_demo=True, database_url=None),
        ScaffoldPhaseLogWriter,
    )


def test_create_error_log_writer_empty_url_is_scaffold() -> None:
    assert isinstance(
        create_error_log_writer(scaffold_demo=False, database_url=None),
        ScaffoldErrorLogWriter,
    )
    assert isinstance(
        create_error_log_writer(scaffold_demo=False, database_url=""),
        ScaffoldErrorLogWriter,
    )
    assert isinstance(
        create_error_log_writer(scaffold_demo=False, database_url="scaffold://local"),
        ScaffoldErrorLogWriter,
    )


def test_create_batch_observability_writers_postgres_injected() -> None:
    db = ScaffoldDbWriter()
    obs = create_batch_observability_writers(
        scaffold_demo=False,
        database_url="postgresql://user:pass@localhost/db",
        db_writer=db,
    )
    assert isinstance(obs.phase_log_writer, PostgresPhaseLogWriter)
    assert isinstance(obs.error_log_writer, PostgresErrorLogWriter)
    assert isinstance(obs.api_call_log_writer, PostgresApiCallLogWriter)


def test_map_app_phase_genre_sync() -> None:
    assert map_app_phase_to_ddl("plan") == "batch_started"
    assert map_app_phase_to_ddl("finalize") == "batch_completed"
    assert map_app_phase_to_ddl("summary_created") == "summary_created"
    assert map_app_phase_to_ddl("fetch") is None
    assert map_app_phase_status("succeeded") == "succeeded"
    assert map_app_phase_status("failed") == "failed"
    assert map_app_phase_status("partially_succeeded") == "failed"


def test_genre_sync_repos_maps_plan_finalize_to_db() -> None:
    db = ScaffoldDbWriter()
    phase_writer = PostgresPhaseLogWriter(db_writer=db)
    error_writer = PostgresErrorLogWriter(db_writer=db)
    repos = GenreSyncRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=db,
        bucket="scaffold-raw",
        phase_log_writer=phase_writer,
        error_log_writer=error_writer,
    )
    run_id = str(uuid4())
    repos.bind_run(batch_run_id=run_id, trace_id="t1")

    repos.record_phase(phase="plan", status="succeeded")
    repos.record_phase(phase="finalize", status="succeeded")
    repos.record_phase(phase="fetch", status="succeeded")  # unmapped → in-memory only
    repos.record_error(code="GRS-BAT-001", summary="empty", genre_id="0")

    assert repos.phase_logs == [
        {"phase": "plan", "status": "succeeded"},
        {"phase": "finalize", "status": "succeeded"},
        {"phase": "fetch", "status": "succeeded"},
    ]
    assert len(repos.error_logs) == 1

    phase_calls = [c for c in db.write_calls if c["table"] == "phase_log"]
    error_calls = [c for c in db.write_calls if c["table"] == "error_log"]
    assert len(phase_calls) == 2
    assert phase_calls[0]["rows"][0]["phase_name"] == "batch_started"
    assert phase_calls[1]["rows"][0]["phase_name"] == "batch_completed"
    assert len(error_calls) == 1
    assert error_calls[0]["rows"][0]["error_code"] == "GRS-BAT-001"
    assert error_calls[0]["rows"][0]["service"] == "batch"
    assert error_calls[0]["rows"][0]["owner_type"] == "batch_run"


def test_genre_sync_repos_without_bind_keeps_memory_only() -> None:
    db = ScaffoldDbWriter()
    repos = GenreSyncRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=db,
        bucket="scaffold-raw",
        phase_log_writer=PostgresPhaseLogWriter(db_writer=db),
        error_log_writer=PostgresErrorLogWriter(db_writer=db),
    )
    repos.record_phase(phase="plan", status="succeeded")
    repos.record_error(code="GRS-BAT-001", summary="x")
    assert len(repos.phase_logs) == 1
    assert len(repos.error_logs) == 1
    assert db.write_calls == []


def test_genre_sync_finalize_partially_succeeded_maps_to_failed_status() -> None:
    db = ScaffoldDbWriter()
    phase_writer = PostgresPhaseLogWriter(db_writer=db)
    repos = GenreSyncRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=db,
        bucket="scaffold-raw",
        phase_log_writer=phase_writer,
    )
    run_id = str(uuid4())
    repos.bind_run(batch_run_id=run_id)
    repos.record_phase(phase="finalize", status="partially_succeeded")

    row = db.write_calls[0]["rows"][0]
    assert row["phase_name"] == "batch_completed"
    assert row["phase_status"] == "failed"
    detail = row["detail_json"]
    if hasattr(detail, "obj"):
        detail = detail.obj
    assert detail["app_phase"] == "finalize"
