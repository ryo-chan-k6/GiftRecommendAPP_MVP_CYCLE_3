"""API call log writers for Batch observability (scaffold / Postgres ``api_call_log``)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from batch.infrastructure.db import DbWriter

_API_CALL_LOG_TABLE = "api_call_log"
_SOURCE_RAKUTEN = "rakuten"
_SOURCE_OPENAI = "openai"

# DDL chk_api_call_log_source_mvp（Wave 5: rakuten | openai）
ALLOWED_SOURCES: frozenset[str] = frozenset({_SOURCE_RAKUTEN, _SOURCE_OPENAI})

# DDL chk_api_call_log_source_api（Wave 5: + item_embedding）
ALLOWED_SOURCE_APIS: frozenset[str] = frozenset(
    {
        "item_search",
        "item_ranking",
        "genre_search",
        "attribute_search",
        "item_embedding",
    }
)

# DDL chk_api_call_log_status
ALLOWED_CALL_STATUSES: frozenset[str] = frozenset(
    {
        "requested",
        "succeeded",
        "failed",
        "rate_limited",
        "skipped",
    }
)
_TERMINAL_CALL_STATUSES: frozenset[str] = frozenset(
    {"succeeded", "failed", "rate_limited", "skipped"}
)

# Keys that must not land in request_params_json (Observability §14.3 / case-insensitive).
_SENSITIVE_PARAM_KEYS: frozenset[str] = frozenset(
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


def _require_uuid(value: str, *, field_name: str) -> str:
    try:
        UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(
            f"{field_name} must be a UUID string for api_call_log, got {value!r}"
        ) from exc
    return value


def _sanitize_params(params: dict[str, Any] | None) -> dict[str, Any]:
    """Strip sensitive keys from request params; never store Authorization / secrets."""

    if not params:
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in params.items():
        if str(key).lower() in _SENSITIVE_PARAM_KEYS:
            continue
        cleaned[key] = value
    return cleaned


def _stable_params_hash(params: dict[str, Any]) -> str:
    """SHA-256 hex of stable JSON (sort_keys). Assumes secret keys already stripped."""

    body = json.dumps(params, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(body).hexdigest()


def _as_jsonb(value: dict[str, Any]) -> object:
    """Adapt dict for PostgreSQL jsonb placeholders (Scaffold では dict のまま可)."""

    try:
        from psycopg.types.json import Json
    except ImportError:  # pragma: no cover — CI/scaffold without psycopg
        return value
    return Json(value)


class ApiCallLogWriter(Protocol):
    """Writes external API call audit rows (scaffold or Postgres ``api_call_log``)."""

    def record_call(
        self,
        *,
        api_call_log_id: str,
        batch_run_id: str,
        source_api: str,
        call_status: str,
        source: str = _SOURCE_RAKUTEN,
        request_params_json: dict[str, Any] | None = None,
        request_params_hash: str | None = None,
        error_code: str | None = None,
        response_status: int | None = None,
        item_count: int = 0,
        trace_id: str | None = None,
        fetch_cursor_id: str | None = None,
        api_version: str | None = None,
        duration_ms: int | None = None,
    ) -> dict[str, object]: ...


@dataclass
class ScaffoldApiCallLogWriter:
    """In-memory API call log writer for ``--scaffold-demo`` / unit tests."""

    records: list[dict[str, object]] = field(default_factory=list)

    def record_call(
        self,
        *,
        api_call_log_id: str,
        batch_run_id: str,
        source_api: str,
        call_status: str,
        source: str = _SOURCE_RAKUTEN,
        request_params_json: dict[str, Any] | None = None,
        request_params_hash: str | None = None,
        error_code: str | None = None,
        response_status: int | None = None,
        item_count: int = 0,
        trace_id: str | None = None,
        fetch_cursor_id: str | None = None,
        api_version: str | None = None,
        duration_ms: int | None = None,
    ) -> dict[str, object]:
        cleaned = _sanitize_params(request_params_json)
        params_hash = request_params_hash or _stable_params_hash(cleaned)
        record: dict[str, object] = {
            "api_call_log_id": api_call_log_id,
            "batch_run_id": batch_run_id,
            "source": source,
            "source_api": source_api,
            "call_status": call_status,
            "request_params_json": cleaned,
            "request_params_hash": params_hash,
            "error_code": error_code,
            "response_status": response_status,
            "item_count": item_count,
            "trace_id": trace_id,
            "fetch_cursor_id": fetch_cursor_id,
            "api_version": api_version,
            "duration_ms": duration_ms,
        }
        self.records.append(record)
        return record


@dataclass
class PostgresApiCallLogWriter:
    """MOD-BATCH-046 path: write ``api_call_log`` via DbWriter.

    既定 ``source=rakuten``（001〜004）。BATCH-015 Embedding は ``source=openai``。
    ``source`` は API 提供者識別であり、``item.source``（マーケット）とは別概念。
    """

    db_writer: DbWriter
    records: list[dict[str, object]] = field(default_factory=list)

    def record_call(
        self,
        *,
        api_call_log_id: str,
        batch_run_id: str,
        source_api: str,
        call_status: str,
        source: str = _SOURCE_RAKUTEN,
        request_params_json: dict[str, Any] | None = None,
        request_params_hash: str | None = None,
        error_code: str | None = None,
        response_status: int | None = None,
        item_count: int = 0,
        trace_id: str | None = None,
        fetch_cursor_id: str | None = None,
        api_version: str | None = None,
        duration_ms: int | None = None,
    ) -> dict[str, object]:
        call_id = _require_uuid(api_call_log_id, field_name="api_call_log_id")
        run_id = _require_uuid(batch_run_id, field_name="batch_run_id")
        if source not in ALLOWED_SOURCES:
            raise ValueError(
                f"source must be one of {sorted(ALLOWED_SOURCES)}, got {source!r}"
            )
        if source_api not in ALLOWED_SOURCE_APIS:
            raise ValueError(
                f"source_api must be one of {sorted(ALLOWED_SOURCE_APIS)}, got {source_api!r}"
            )
        if call_status not in ALLOWED_CALL_STATUSES:
            raise ValueError(
                f"call_status must be one of {sorted(ALLOWED_CALL_STATUSES)}, got {call_status!r}"
            )
        if item_count < 0:
            raise ValueError(f"item_count must be >= 0, got {item_count!r}")
        if duration_ms is not None and duration_ms < 0:
            raise ValueError(f"duration_ms must be >= 0 or None, got {duration_ms!r}")
        if fetch_cursor_id is not None:
            _require_uuid(fetch_cursor_id, field_name="fetch_cursor_id")

        cleaned = _sanitize_params(request_params_json)
        params_hash = request_params_hash or _stable_params_hash(cleaned)
        now = datetime.now(UTC)
        completed_at: datetime | None = now if call_status in _TERMINAL_CALL_STATUSES else None

        row: dict[str, object] = {
            "api_call_log_id": call_id,
            "batch_run_id": run_id,
            "fetch_cursor_id": fetch_cursor_id,
            "trace_id": trace_id,
            "source": source,
            "source_api": source_api,
            "request_params_hash": params_hash,
            "request_params_json": _as_jsonb(cleaned),
            "api_version": api_version,
            "response_status": response_status,
            "call_status": call_status,
            "item_count": item_count,
            "requested_at": now,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "error_code": error_code,
        }
        self.db_writer.write_rows(_API_CALL_LOG_TABLE, (row,))

        record: dict[str, object] = {
            "api_call_log_id": call_id,
            "batch_run_id": run_id,
            "source": source,
            "source_api": source_api,
            "call_status": call_status,
            "request_params_json": cleaned,
            "request_params_hash": params_hash,
            "error_code": error_code,
            "response_status": response_status,
            "item_count": item_count,
            "trace_id": trace_id,
            "fetch_cursor_id": fetch_cursor_id,
            "api_version": api_version,
            "duration_ms": duration_ms,
            "completed_at": completed_at,
        }
        self.records.append(record)
        return record
