"""Error log writers for Batch observability (scaffold / Postgres ``error_log``)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from batch.infrastructure.db import DbWriter

_ERROR_LOG_TABLE = "error_log"
_OWNER_TYPE_BATCH_RUN = "batch_run"
_SERVICE_BATCH = "batch"

# DDL chk_error_log_error_code_format: ^GRS-[A-Z]{3}-[0-9]{3}$
_ERROR_CODE_PATTERN = re.compile(r"^GRS-[A-Z]{3}-[0-9]{3}$")

ALLOWED_SEVERITIES: frozenset[str] = frozenset({"warn", "error", "critical"})

# Keys that must not land in error_detail_json (case-insensitive match).
_SENSITIVE_DETAIL_KEYS: frozenset[str] = frozenset(
    {
        "authorization",
        "access_key",
        "secret",
        "secret_key",
        "password",
        "token",
        "api_key",
        "apikey",
        "client_secret",
        "private_key",
        "database_url",
        "url",
        "uri",
        "cookie",
        "session",
        "bearer",
        "refresh_token",
        "access_token",
    }
)


def _require_uuid_batch_run_id(batch_run_id: str) -> str:
    try:
        UUID(batch_run_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(
            f"batch_run_id must be a UUID string for error_log, got {batch_run_id!r}"
        ) from exc
    return batch_run_id


def _validate_error_code(error_code: str) -> str:
    if not _ERROR_CODE_PATTERN.fullmatch(error_code):
        raise ValueError(
            "error_code must match GRS-XXX-NNN "
            f"(DDL ^GRS-[A-Z]{{3}}-[0-9]{{3}}$), got {error_code!r}"
        )
    return error_code


def _sanitize_detail(detail: dict[str, Any] | None) -> dict[str, Any]:
    """Strip sensitive keys from detail; never store Authorization / URL / secrets."""

    if not detail:
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in detail.items():
        if str(key).lower() in _SENSITIVE_DETAIL_KEYS:
            continue
        cleaned[key] = value
    return cleaned


def _as_jsonb(value: dict[str, Any]) -> object:
    """Adapt dict for PostgreSQL jsonb placeholders (Scaffold では dict のまま可)."""

    try:
        from psycopg.types.json import Json
    except ImportError:  # pragma: no cover — CI/scaffold without psycopg
        return value
    return Json(value)


class ErrorLogWriter(Protocol):
    """Writes batch error events (in-memory scaffold or Postgres ``error_log``)."""

    def record_error(
        self,
        *,
        batch_run_id: str,
        error_code: str,
        error_message: str,
        severity: str = "error",
        retryable: bool = False,
        detail: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> dict[str, object]: ...


@dataclass
class ScaffoldErrorLogWriter:
    """In-memory error log writer for ``--scaffold-demo`` / unit tests."""

    records: list[dict[str, object]] = field(default_factory=list)

    def record_error(
        self,
        *,
        batch_run_id: str,
        error_code: str,
        error_message: str,
        severity: str = "error",
        retryable: bool = False,
        detail: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> dict[str, object]:
        record: dict[str, object] = {
            "batch_run_id": batch_run_id,
            "error_code": error_code,
            "error_message": error_message,
            "severity": severity,
            "retryable": retryable,
            "detail": _sanitize_detail(detail),
            "trace_id": trace_id,
        }
        self.records.append(record)
        return record


@dataclass
class PostgresErrorLogWriter:
    """Batch Error Handler path: write ``error_log`` via DbWriter (``service=batch``)."""

    db_writer: DbWriter
    records: list[dict[str, object]] = field(default_factory=list)

    def record_error(
        self,
        *,
        batch_run_id: str,
        error_code: str,
        error_message: str,
        severity: str = "error",
        retryable: bool = False,
        detail: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> dict[str, object]:
        owner_id = _require_uuid_batch_run_id(batch_run_id)
        code = _validate_error_code(error_code)
        if severity not in ALLOWED_SEVERITIES:
            raise ValueError(
                f"severity must be one of {sorted(ALLOWED_SEVERITIES)}, got {severity!r}"
            )
        cleaned_detail = _sanitize_detail(detail)
        now = datetime.now(UTC)

        row: dict[str, object] = {
            "trace_id": trace_id,
            "owner_type": _OWNER_TYPE_BATCH_RUN,
            "owner_id": owner_id,
            "service": _SERVICE_BATCH,
            "error_code": code,
            "error_message": error_message,
            "severity": severity,
            "retryable": retryable,
            "error_detail_json": _as_jsonb(cleaned_detail),
            "occurred_at": now,
        }
        self.db_writer.write_rows(_ERROR_LOG_TABLE, (row,))

        record: dict[str, object] = {
            "batch_run_id": owner_id,
            "error_code": code,
            "error_message": error_message,
            "severity": severity,
            "retryable": retryable,
            "detail": cleaned_detail,
            "trace_id": trace_id,
        }
        self.records.append(record)
        return record
