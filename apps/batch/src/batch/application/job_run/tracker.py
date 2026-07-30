"""Job run tracking for batch application services (scaffold / Postgres)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal, Protocol
from uuid import UUID

from batch.infrastructure.db import DbWriter, create_db_writer

JobRunStatus = Literal["pending", "running", "succeeded", "partially_succeeded", "failed"]

_TERMINAL_COMPLETE_STATUSES: frozenset[str] = frozenset(
    {"succeeded", "partially_succeeded", "failed"}
)
_BATCH_RUN_LOG_TABLE = "batch_run_log"
# 複合子共有 pipeline UUID 用の batch_name
PIPELINE_ITEM_IMPORT_BATCH_NAME = "item_import_pipeline"
PIPELINE_ITEM_MEANING_BATCH_NAME = "item_meaning_pipeline"


@dataclass(frozen=True)
class JobRunRecord:
    """Snapshot of a batch job run for scaffold / unit tests."""

    batch_id: str
    job_run_id: str
    status: JobRunStatus


class JobRunTracker(Protocol):
    """Tracks batch job run lifecycle (in-memory scaffold or Postgres ``batch_run_log``)."""

    def start(self, *, batch_id: str, job_run_id: str) -> JobRunRecord: ...

    def complete(self, *, batch_id: str, job_run_id: str, status: JobRunStatus) -> JobRunRecord: ...

    def ensure_batch_run(self, *, batch_id: str, batch_run_id: str) -> JobRunRecord: ...


def _require_uuid_job_run_id(job_run_id: str) -> str:
    """Validate ``job_run_id`` as a UUID string used as ``batch_run_id``."""

    try:
        UUID(job_run_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(
            f"job_run_id must be a UUID string for Postgres batch_run_log, got {job_run_id!r}"
        ) from exc
    return job_run_id


@dataclass
class ScaffoldJobRunTracker:
    """In-memory tracker for ``--scaffold-demo`` / unit tests (no DB I/O)."""

    records: list[JobRunRecord] = field(default_factory=list)

    def start(self, *, batch_id: str, job_run_id: str) -> JobRunRecord:
        record = JobRunRecord(batch_id=batch_id, job_run_id=job_run_id, status="running")
        self.records.append(record)
        return record

    def complete(self, *, batch_id: str, job_run_id: str, status: JobRunStatus) -> JobRunRecord:
        record = JobRunRecord(batch_id=batch_id, job_run_id=job_run_id, status=status)
        self.records.append(record)
        return record

    def ensure_batch_run(self, *, batch_id: str, batch_run_id: str) -> JobRunRecord:
        """Idempotent in-memory ensure（既に同 ID があれば先頭一致を返す）."""

        for record in self.records:
            if record.job_run_id == batch_run_id:
                return record
        return self.start(batch_id=batch_id, job_run_id=batch_run_id)


@dataclass
class PostgresJobRunTracker:
    """IF-DB-BATCH-001 / MOD-BATCH-045: write job lifecycle to ``batch_run_log`` via DbWriter."""

    db_writer: DbWriter
    records: list[JobRunRecord] = field(default_factory=list)
    _started_at: dict[str, datetime] = field(default_factory=dict, repr=False)

    def start(self, *, batch_id: str, job_run_id: str) -> JobRunRecord:
        batch_run_id = _require_uuid_job_run_id(job_run_id)
        started_at = datetime.now(UTC)
        self.db_writer.write_rows(
            _BATCH_RUN_LOG_TABLE,
            (
                {
                    "batch_run_id": batch_run_id,
                    "batch_name": batch_id,
                    "run_status": "running",
                    "started_at": started_at,
                    "success_count": 0,
                    "failed_count": 0,
                    "skipped_count": 0,
                },
            ),
        )
        self._started_at[batch_run_id] = started_at
        record = JobRunRecord(batch_id=batch_id, job_run_id=batch_run_id, status="running")
        self.records.append(record)
        return record

    def ensure_batch_run(self, *, batch_id: str, batch_run_id: str) -> JobRunRecord:
        """Ensure ``batch_run_log`` row for pipeline UUID（INSERT ON CONFLICT DO NOTHING）."""

        run_id = _require_uuid_job_run_id(batch_run_id)
        started_at = datetime.now(UTC)
        self.db_writer.upsert_rows(
            _BATCH_RUN_LOG_TABLE,
            (
                {
                    "batch_run_id": run_id,
                    "batch_name": batch_id,
                    "run_status": "running",
                    "started_at": started_at,
                    "success_count": 0,
                    "failed_count": 0,
                    "skipped_count": 0,
                },
            ),
            conflict_columns=("batch_run_id",),
            update_columns=(),
        )
        self._started_at.setdefault(run_id, started_at)
        record = JobRunRecord(batch_id=batch_id, job_run_id=run_id, status="running")
        self.records.append(record)
        return record

    def complete(self, *, batch_id: str, job_run_id: str, status: JobRunStatus) -> JobRunRecord:
        if status not in _TERMINAL_COMPLETE_STATUSES:
            raise ValueError(
                "complete status must be one of "
                f"{sorted(_TERMINAL_COMPLETE_STATUSES)}, got {status!r}"
            )
        batch_run_id = _require_uuid_job_run_id(job_run_id)
        completed_at = datetime.now(UTC)
        started_at = self._started_at.get(batch_run_id)
        duration_ms: int | None
        if started_at is None:
            duration_ms = None
        else:
            duration_ms = max(
                0, int((completed_at - started_at).total_seconds() * 1000)
            )

        self.db_writer.update_rows(
            _BATCH_RUN_LOG_TABLE,
            set_values={
                "run_status": status,
                "completed_at": completed_at,
                "duration_ms": duration_ms,
                "updated_at": completed_at,
            },
            equals=(("batch_run_id", batch_run_id),),
        )
        record = JobRunRecord(batch_id=batch_id, job_run_id=batch_run_id, status=status)
        self.records.append(record)
        return record


def create_job_run_tracker(
    *,
    scaffold_demo: bool,
    database_url: str | None,
    db_writer: DbWriter | None = None,
) -> JobRunTracker:
    """Resolve JobRunTracker for CLI jobs (same switch policy as ``resolve_job_db_writer``).

    - ``scaffold_demo`` / unset・empty / ``scaffold://...`` → ``ScaffoldJobRunTracker``
    - otherwise → ``PostgresJobRunTracker``（``db_writer`` 無ければ ``create_db_writer``）
    """

    if scaffold_demo:
        return ScaffoldJobRunTracker()
    if not database_url or database_url.startswith("scaffold://"):
        return ScaffoldJobRunTracker()
    writer = db_writer if db_writer is not None else create_db_writer(database_url)
    return PostgresJobRunTracker(db_writer=writer)
