"""PostgreSQL ErrorLogRepository (MOD-RECO-029)."""

from __future__ import annotations

from dataclasses import dataclass

from psycopg.types.json import Json

from reco.infrastructure.db.application_bootstrap import ensure_observability_application_packages
from reco.infrastructure.db.session import DatabaseSession

ensure_observability_application_packages()
from reco.application.error_log_writer.models import ErrorLogRecord

_INSERT_SQL = """
INSERT INTO error_log (
  trace_id,
  request_id,
  owner_type,
  owner_id,
  service,
  error_code,
  error_message,
  severity,
  retryable,
  error_detail_json,
  occurred_at
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING error_log_id
"""


@dataclass
class PostgresErrorLogRepository:
    """PostgreSQL implementation aligned with ``InMemoryErrorLogRepository``."""

    session: DatabaseSession

    def insert(self, record: ErrorLogRecord) -> str:
        row = self.session.query_one(
            _INSERT_SQL,
            (
                record.trace_id,
                record.request_id,
                record.owner_type,
                record.owner_id,
                record.service,
                record.error_code,
                record.error_message,
                record.severity,
                record.retryable,
                Json(record.error_detail_json),
                record.occurred_at,
            ),
        )
        if row is None:
            raise RuntimeError("error_log insert failed")
        return str(row["error_log_id"])
