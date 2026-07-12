"""In-memory Phase Log repository for scaffold and unit tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from .models import PhaseLogRecord


@dataclass
class StoredPhaseLogRecord:
    """Mutable in-memory phase_log row."""

    phase_log_id: str
    trace_id: str | None
    owner_type: str
    owner_id: str
    phase_name: str
    phase_status: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    error_code: str | None = None
    detail_json: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class InMemoryPhaseLogRepository:
    """Phase4a in-memory phase_log store."""

    records: dict[str, StoredPhaseLogRecord] = field(default_factory=dict)
    should_fail_on_insert: bool = False
    should_fail_on_update: bool = False

    def insert_started(self, record: PhaseLogRecord) -> str:
        if self.should_fail_on_insert:
            raise RuntimeError("phase_log insert failed")

        now = datetime.now(UTC)
        phase_log_id = str(uuid4())
        self.records[phase_log_id] = StoredPhaseLogRecord(
            phase_log_id=phase_log_id,
            trace_id=record.trace_id,
            owner_type=record.owner_type,
            owner_id=record.owner_id,
            phase_name=record.phase_name,
            phase_status=record.phase_status,
            started_at=record.started_at,
            detail_json=dict(record.detail_json),
            created_at=now,
            updated_at=now,
        )
        return phase_log_id

    def update_terminal(
        self,
        phase_log_id: str,
        *,
        phase_status: str,
        completed_at: datetime,
        duration_ms: int | None,
        error_code: str | None,
        detail_json: dict[str, object],
    ) -> None:
        if self.should_fail_on_update:
            raise RuntimeError("phase_log update failed")

        current = self.records.get(phase_log_id)
        if current is None:
            raise KeyError(f"phase_log not found: {phase_log_id}")
        if current.phase_status != "started":
            raise ValueError(
                f"phase_log terminal update requires started status: {phase_log_id}"
            )

        now = datetime.now(UTC)
        self.records[phase_log_id] = StoredPhaseLogRecord(
            phase_log_id=current.phase_log_id,
            trace_id=current.trace_id,
            owner_type=current.owner_type,
            owner_id=current.owner_id,
            phase_name=current.phase_name,
            phase_status=phase_status,
            started_at=current.started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            error_code=error_code,
            detail_json=dict(detail_json),
            created_at=current.created_at,
            updated_at=now,
        )
