"""Phase log writers for Batch observability (scaffold / Postgres ``phase_log``)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from batch.infrastructure.db import DbWriter

_PHASE_LOG_TABLE = "phase_log"
_OWNER_TYPE_BATCH_RUN = "batch_run"

# DDL chk_phase_log_phase_name_batch（owner_type=batch_run）
ALLOWED_BATCH_PHASE_NAMES: frozenset[str] = frozenset(
    {
        "batch_started",
        "cursor_loaded",
        "external_api_called",
        "raw_saved",
        "raw_metadata_saved",
        "staging_transformed",
        "diff_judged",
        "item_imported",
        "item_image_imported",
        "popularity_signal_imported",
        "item_feature_generated",
        "item_embedding_generated",
        "feature_distribution_metric_recorded",
        "summary_created",
        "batch_completed",
    }
)

ALLOWED_PHASE_STATUSES: frozenset[str] = frozenset(
    {"started", "succeeded", "failed", "skipped"}
)
_TERMINAL_PHASE_STATUSES: frozenset[str] = frozenset({"succeeded", "failed", "skipped"})


def _require_uuid_batch_run_id(batch_run_id: str) -> str:
    try:
        UUID(batch_run_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(
            f"batch_run_id must be a UUID string for phase_log, got {batch_run_id!r}"
        ) from exc
    return batch_run_id


def _as_jsonb(value: dict[str, Any]) -> object:
    """Adapt dict for PostgreSQL jsonb placeholders (Scaffold では dict のまま可)."""

    try:
        from psycopg.types.json import Json
    except ImportError:  # pragma: no cover — CI/scaffold without psycopg
        return value
    return Json(value)


class PhaseLogWriter(Protocol):
    """Writes batch phase events (in-memory scaffold or Postgres ``phase_log``)."""

    def record_phase(
        self,
        *,
        batch_run_id: str,
        phase_name: str,
        phase_status: str,
        app_phase: str | None = None,
        error_code: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, object]: ...


@dataclass
class ScaffoldPhaseLogWriter:
    """In-memory phase log writer for ``--scaffold-demo`` / unit tests."""

    records: list[dict[str, object]] = field(default_factory=list)

    def record_phase(
        self,
        *,
        batch_run_id: str,
        phase_name: str,
        phase_status: str,
        app_phase: str | None = None,
        error_code: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, object]:
        record: dict[str, object] = {
            "batch_run_id": batch_run_id,
            "phase_name": phase_name,
            "phase_status": phase_status,
            "app_phase": app_phase,
            "error_code": error_code,
            "trace_id": trace_id,
        }
        self.records.append(record)
        return record


@dataclass
class PostgresPhaseLogWriter:
    """Batch Logger path: write ``phase_log`` via DbWriter (``owner_type=batch_run``)."""

    db_writer: DbWriter
    records: list[dict[str, object]] = field(default_factory=list)

    def record_phase(
        self,
        *,
        batch_run_id: str,
        phase_name: str,
        phase_status: str,
        app_phase: str | None = None,
        error_code: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, object]:
        owner_id = _require_uuid_batch_run_id(batch_run_id)
        if phase_name not in ALLOWED_BATCH_PHASE_NAMES:
            raise ValueError(
                f"phase_name {phase_name!r} is not allowed for owner_type=batch_run "
                f"(DDL CHECK). Allowed: {sorted(ALLOWED_BATCH_PHASE_NAMES)}"
            )
        if phase_status not in ALLOWED_PHASE_STATUSES:
            raise ValueError(
                f"phase_status must be one of {sorted(ALLOWED_PHASE_STATUSES)}, "
                f"got {phase_status!r}"
            )

        now = datetime.now(UTC)
        detail: dict[str, Any] = {}
        if app_phase is not None:
            detail["app_phase"] = app_phase

        completed_at: datetime | None
        duration_ms: int | None
        if phase_status in _TERMINAL_PHASE_STATUSES:
            completed_at = now
            duration_ms = 0
        else:
            completed_at = None
            duration_ms = None

        row: dict[str, object] = {
            "trace_id": trace_id,
            "owner_type": _OWNER_TYPE_BATCH_RUN,
            "owner_id": owner_id,
            "phase_name": phase_name,
            "phase_status": phase_status,
            "started_at": now,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "error_code": error_code,
            "detail_json": _as_jsonb(detail),
        }
        self.db_writer.write_rows(_PHASE_LOG_TABLE, (row,))

        record: dict[str, object] = {
            "batch_run_id": owner_id,
            "phase_name": phase_name,
            "phase_status": phase_status,
            "app_phase": app_phase,
            "error_code": error_code,
            "trace_id": trace_id,
            "detail_json": detail,
        }
        self.records.append(record)
        return record
