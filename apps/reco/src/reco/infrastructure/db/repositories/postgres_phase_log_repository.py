"""PostgreSQL PhaseLogRepository (MOD-RECO-028)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from psycopg.types.json import Json

from reco.infrastructure.db.application_bootstrap import ensure_observability_application_packages
from reco.infrastructure.db.session import DatabaseSession

ensure_observability_application_packages()
from reco.application.phase_log_writer.models import PhaseLogRecord

_INSERT_STARTED_SQL = """
INSERT INTO phase_log (
  trace_id,
  owner_type,
  owner_id,
  phase_name,
  phase_status,
  started_at,
  detail_json,
  created_at,
  updated_at
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING phase_log_id
"""

_UPDATE_TERMINAL_SQL = """
UPDATE phase_log
SET
  phase_status = %s,
  completed_at = %s,
  duration_ms = %s,
  error_code = %s,
  detail_json = %s,
  updated_at = %s
WHERE phase_log_id = %s
  AND phase_status = 'started'
RETURNING phase_log_id
"""


@dataclass
class PostgresPhaseLogRepository:
    """PostgreSQL implementation aligned with ``InMemoryPhaseLogRepository``."""

    session: DatabaseSession

    def insert_started(self, record: PhaseLogRecord) -> str:
        now = datetime.now(UTC)
        row = self.session.query_one(
            _INSERT_STARTED_SQL,
            (
                record.trace_id,
                record.owner_type,
                record.owner_id,
                record.phase_name,
                record.phase_status,
                record.started_at,
                Json(record.detail_json),
                now,
                now,
            ),
        )
        if row is None:
            raise RuntimeError("phase_log insert failed")
        return str(row["phase_log_id"])

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
        now = datetime.now(UTC)
        row = self.session.query_one(
            _UPDATE_TERMINAL_SQL,
            (
                phase_status,
                completed_at,
                duration_ms,
                error_code,
                Json(detail_json),
                now,
                phase_log_id,
            ),
        )
        if row is None:
            current = self.session.query_one(
                "SELECT phase_status FROM phase_log WHERE phase_log_id = %s",
                (phase_log_id,),
            )
            if current is None:
                raise KeyError(f"phase_log not found: {phase_log_id}")
            raise ValueError(
                f"phase_log terminal update requires started status: {phase_log_id}"
            )
        return None
