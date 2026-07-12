"""Job run tracking scaffold for batch application services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

JobRunStatus = Literal["pending", "running", "succeeded", "partially_succeeded", "failed"]


@dataclass(frozen=True)
class JobRunRecord:
    """Snapshot of a batch job run for Phase4a scaffold tests."""

    batch_id: str
    job_run_id: str
    status: JobRunStatus


class JobRunTracker(Protocol):
    """Tracks batch job run lifecycle without a real database."""

    def start(self, *, batch_id: str, job_run_id: str) -> JobRunRecord: ...

    def complete(self, *, batch_id: str, job_run_id: str, status: JobRunStatus) -> JobRunRecord: ...


@dataclass
class ScaffoldJobRunTracker:
    """Phase4a placeholder tracker that records lifecycle transitions in memory."""

    records: list[JobRunRecord] = field(default_factory=list)

    def start(self, *, batch_id: str, job_run_id: str) -> JobRunRecord:
        record = JobRunRecord(batch_id=batch_id, job_run_id=job_run_id, status="running")
        self.records.append(record)
        return record

    def complete(self, *, batch_id: str, job_run_id: str, status: JobRunStatus) -> JobRunRecord:
        record = JobRunRecord(batch_id=batch_id, job_run_id=job_run_id, status=status)
        self.records.append(record)
        return record
