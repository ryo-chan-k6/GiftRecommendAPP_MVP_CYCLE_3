"""Unit tests for JobRunTracker (Scaffold / Postgres batch_run_log)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from batch.application.job_run import (
    PostgresJobRunTracker,
    ScaffoldJobRunTracker,
    create_job_run_tracker,
)
from batch.infrastructure.db import ScaffoldDbWriter


def test_scaffold_job_run_tracker_records_lifecycle() -> None:
    tracker = ScaffoldJobRunTracker()

    started = tracker.start(batch_id="BATCH-001", job_run_id="job-scaffold")
    completed = tracker.complete(
        batch_id="BATCH-001", job_run_id="job-scaffold", status="succeeded"
    )

    assert started.status == "running"
    assert completed.status == "succeeded"
    assert len(tracker.records) == 2


def test_postgres_start_writes_batch_run_log_running() -> None:
    writer = ScaffoldDbWriter()
    tracker = PostgresJobRunTracker(db_writer=writer)
    run_id = str(uuid4())

    started = tracker.start(batch_id="BATCH-001", job_run_id=run_id)

    assert started.status == "running"
    assert started.job_run_id == run_id
    assert len(writer.write_calls) == 1
    call = writer.write_calls[0]
    assert call["table"] == "batch_run_log"
    rows = call["rows"]
    assert len(rows) == 1
    row = rows[0]
    assert row["batch_run_id"] == run_id
    assert row["batch_name"] == "BATCH-001"
    assert row["run_status"] == "running"
    assert row["success_count"] == 0
    assert row["failed_count"] == 0
    assert row["skipped_count"] == 0
    assert isinstance(row["started_at"], datetime)
    assert row["started_at"].tzinfo is not None
    assert "batch_type" not in row
    assert "trace_id" not in row
    assert len(tracker.records) == 1


def test_postgres_ensure_batch_run_upserts_do_nothing() -> None:
    from batch.application.job_run import PIPELINE_ITEM_IMPORT_BATCH_NAME

    writer = ScaffoldDbWriter()
    tracker = PostgresJobRunTracker(db_writer=writer)
    pipeline_id = str(uuid4())

    ensured = tracker.ensure_batch_run(
        batch_id=PIPELINE_ITEM_IMPORT_BATCH_NAME,
        batch_run_id=pipeline_id,
    )

    assert ensured.status == "running"
    assert ensured.job_run_id == pipeline_id
    assert writer.write_calls == []
    assert len(writer.upsert_calls) == 1
    call = writer.upsert_calls[0]
    assert call["table"] == "batch_run_log"
    assert call["conflict_columns"] == ("batch_run_id",)
    assert call["update_columns"] == ()
    row = call["rows"][0]
    assert row["batch_run_id"] == pipeline_id
    assert row["batch_name"] == PIPELINE_ITEM_IMPORT_BATCH_NAME
    assert row["run_status"] == "running"


def test_scaffold_ensure_batch_run_is_idempotent() -> None:
    tracker = ScaffoldJobRunTracker()
    first = tracker.ensure_batch_run(batch_id="pipeline", batch_run_id="pipe-1")
    second = tracker.ensure_batch_run(batch_id="pipeline", batch_run_id="pipe-1")
    assert first.job_run_id == "pipe-1"
    assert second.job_run_id == "pipe-1"
    assert len(tracker.records) == 1


def test_postgres_complete_updates_terminal_status() -> None:
    writer = ScaffoldDbWriter()
    tracker = PostgresJobRunTracker(db_writer=writer)
    run_id = str(uuid4())

    tracker.start(batch_id="BATCH-001", job_run_id=run_id)
    completed = tracker.complete(
        batch_id="BATCH-001", job_run_id=run_id, status="succeeded"
    )

    assert completed.status == "succeeded"
    assert len(writer.update_calls) == 1
    call = writer.update_calls[0]
    assert call["table"] == "batch_run_log"
    assert call["equals"] == (("batch_run_id", run_id),)
    set_values = call["set_values"]
    assert set_values["run_status"] == "succeeded"
    assert isinstance(set_values["completed_at"], datetime)
    assert set_values["completed_at"].tzinfo is not None
    assert isinstance(set_values["duration_ms"], int)
    assert set_values["duration_ms"] >= 0
    assert isinstance(set_values["updated_at"], datetime)
    assert len(tracker.records) == 2


@pytest.mark.parametrize("status", ["succeeded", "partially_succeeded", "failed"])
def test_postgres_complete_allows_terminal_statuses(status: str) -> None:
    writer = ScaffoldDbWriter()
    tracker = PostgresJobRunTracker(db_writer=writer)
    run_id = str(uuid4())
    tracker.start(batch_id="BATCH-017", job_run_id=run_id)
    record = tracker.complete(batch_id="BATCH-017", job_run_id=run_id, status=status)  # type: ignore[arg-type]
    assert record.status == status


def test_postgres_complete_rejects_pending() -> None:
    writer = ScaffoldDbWriter()
    tracker = PostgresJobRunTracker(db_writer=writer)
    run_id = str(uuid4())
    tracker.start(batch_id="BATCH-001", job_run_id=run_id)

    with pytest.raises(ValueError, match="complete status must be one of"):
        tracker.complete(batch_id="BATCH-001", job_run_id=run_id, status="pending")


def test_postgres_complete_rejects_running() -> None:
    writer = ScaffoldDbWriter()
    tracker = PostgresJobRunTracker(db_writer=writer)
    run_id = str(uuid4())
    tracker.start(batch_id="BATCH-001", job_run_id=run_id)

    with pytest.raises(ValueError, match="complete status must be one of"):
        tracker.complete(batch_id="BATCH-001", job_run_id=run_id, status="running")


def test_postgres_start_rejects_non_uuid_job_run_id() -> None:
    writer = ScaffoldDbWriter()
    tracker = PostgresJobRunTracker(db_writer=writer)

    with pytest.raises(ValueError, match="UUID"):
        tracker.start(batch_id="BATCH-001", job_run_id="local-run")
    assert writer.write_calls == []


def test_postgres_complete_rejects_non_uuid_job_run_id() -> None:
    writer = ScaffoldDbWriter()
    tracker = PostgresJobRunTracker(db_writer=writer)

    with pytest.raises(ValueError, match="UUID"):
        tracker.complete(
            batch_id="BATCH-001",
            job_run_id="not-a-uuid",
            status="succeeded",
        )
    assert writer.update_calls == []


def test_postgres_complete_duration_null_when_started_at_unknown() -> None:
    writer = ScaffoldDbWriter()
    tracker = PostgresJobRunTracker(db_writer=writer)
    run_id = str(uuid4())

    # complete without prior start in this tracker instance
    tracker.complete(batch_id="BATCH-001", job_run_id=run_id, status="failed")

    set_values = writer.update_calls[0]["set_values"]
    assert set_values["duration_ms"] is None
    assert set_values["run_status"] == "failed"


def test_create_job_run_tracker_scaffold_demo() -> None:
    tracker = create_job_run_tracker(
        scaffold_demo=True,
        database_url="postgresql://localhost:5432/gift",
    )
    assert isinstance(tracker, ScaffoldJobRunTracker)


def test_create_job_run_tracker_empty_url_is_scaffold() -> None:
    assert isinstance(
        create_job_run_tracker(scaffold_demo=False, database_url=None),
        ScaffoldJobRunTracker,
    )
    assert isinstance(
        create_job_run_tracker(scaffold_demo=False, database_url=""),
        ScaffoldJobRunTracker,
    )
    assert isinstance(
        create_job_run_tracker(scaffold_demo=False, database_url="scaffold://local"),
        ScaffoldJobRunTracker,
    )


def test_create_job_run_tracker_postgres_with_injected_writer() -> None:
    writer = ScaffoldDbWriter()
    tracker = create_job_run_tracker(
        scaffold_demo=False,
        database_url="postgresql://localhost:5432/gift",
        db_writer=writer,
    )
    assert isinstance(tracker, PostgresJobRunTracker)
    assert tracker.db_writer is writer


def test_create_job_run_tracker_postgres_without_writer() -> None:
    tracker = create_job_run_tracker(
        scaffold_demo=False,
        database_url="postgresql://localhost:5432/gift",
    )
    assert isinstance(tracker, PostgresJobRunTracker)
    assert tracker.db_writer.backend == "postgres"


def test_postgres_tracker_does_not_log_secrets() -> None:
    writer = ScaffoldDbWriter()
    tracker = PostgresJobRunTracker(db_writer=writer)
    run_id = str(uuid4())
    tracker.start(batch_id="BATCH-001", job_run_id=run_id)
    tracker.complete(batch_id="BATCH-001", job_run_id=run_id, status="succeeded")

    blob = repr(writer.write_calls) + repr(writer.update_calls) + repr(tracker.records)
    for token in (
        "password",
        "DATABASE_URL",
        "postgresql://",
        "Authorization",
        "access_key",
        "secret",
    ):
        assert token not in blob


def test_genre_sync_cli_scaffold_uses_create_job_run_tracker(monkeypatch, capsys) -> None:
    from batch.application.genre_sync import __main__ as cli

    calls: list[dict[str, object]] = []

    def _capture(*, scaffold_demo: bool, database_url: str | None, db_writer=None):
        calls.append(
            {
                "scaffold_demo": scaffold_demo,
                "database_url": database_url,
                "db_writer": db_writer,
            }
        )
        return ScaffoldJobRunTracker()

    monkeypatch.setattr(cli, "create_job_run_tracker", _capture)
    assert cli.main(["--scaffold-demo", "--job-run-id", "cli-demo"]) == 0
    out = capsys.readouterr().out
    assert "BATCH-001 scaffold demo" in out
    assert calls == [
        {"scaffold_demo": True, "database_url": None, "db_writer": None}
    ]


def test_genre_sync_cli_non_demo_wires_tracker_before_live_gate(monkeypatch) -> None:
    """非 demo では live 判定前に create_job_run_tracker を呼ぶ（Postgres 切替の入口）。"""

    from dataclasses import replace

    from batch.application.genre_sync import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings as scaffold_settings

    calls: list[dict[str, object]] = []

    def _capture(*, scaffold_demo: bool, database_url: str | None, db_writer=None):
        calls.append(
            {
                "scaffold_demo": scaffold_demo,
                "database_url": database_url,
                "has_writer": db_writer is not None,
            }
        )
        return ScaffoldJobRunTracker()

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(
            scaffold_settings(),
            database_url="postgresql://localhost:5432/gift",
        ),
    )
    monkeypatch.setattr(cli, "create_db_writer", lambda _url: ScaffoldDbWriter())
    monkeypatch.setattr(cli, "create_job_run_tracker", _capture)

    # live off → exit 3, but tracker factory must already have been called
    assert cli.main(["--job-run-id", str(uuid4())]) == 3
    assert len(calls) == 1
    assert calls[0]["scaffold_demo"] is False
    assert calls[0]["database_url"] == "postgresql://localhost:5432/gift"
    assert calls[0]["has_writer"] is True


def test_started_at_timezone_is_utc() -> None:
    writer = ScaffoldDbWriter()
    tracker = PostgresJobRunTracker(db_writer=writer)
    before = datetime.now(UTC)
    tracker.start(batch_id="BATCH-001", job_run_id=str(uuid4()))
    after = datetime.now(UTC)
    started_at = writer.write_calls[0]["rows"][0]["started_at"]
    assert before <= started_at <= after
    assert started_at.tzinfo == UTC
