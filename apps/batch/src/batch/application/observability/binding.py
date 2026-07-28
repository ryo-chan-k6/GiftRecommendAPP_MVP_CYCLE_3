"""Thin helpers to mirror genre_sync observability write behavior across Batches.

In-memory lists are always updated. DB writers fire only when ``bind_run`` has set
``batch_run_id`` and the corresponding writer is injected.
"""

from __future__ import annotations

from typing import Any

from batch.application.observability.api_call_log import ApiCallLogWriter
from batch.application.observability.error_log import ErrorLogWriter
from batch.application.observability.mapping import (
    map_app_phase_status,
    map_app_phase_to_ddl,
    warn_unmapped_app_phase,
)
from batch.application.observability.phase_log import PhaseLogWriter


def emit_phase(
    *,
    phase_logs: list[dict[str, object]],
    phase_log_writer: PhaseLogWriter | None,
    batch_run_id: str | None,
    trace_id: str | None,
    phase: str,
    status: str,
) -> None:
    """Append in-memory phase log and optionally write mapped DDL phase to DB."""

    phase_logs.append({"phase": phase, "status": status})
    writer = phase_log_writer
    if writer is None or batch_run_id is None:
        return
    ddl_phase = map_app_phase_to_ddl(phase)
    if ddl_phase is None:
        warn_unmapped_app_phase(phase)
        return
    writer.record_phase(
        batch_run_id=batch_run_id,
        phase_name=ddl_phase,
        phase_status=map_app_phase_status(status),
        app_phase=phase,
        trace_id=trace_id,
    )


def emit_error(
    *,
    error_logs: list[dict[str, object]],
    error_log_writer: ErrorLogWriter | None,
    batch_run_id: str | None,
    trace_id: str | None,
    code: str,
    summary: str,
    memory_extra: dict[str, object] | None = None,
    detail: dict[str, object] | None = None,
) -> None:
    """Append in-memory error log and optionally write ``error_log`` to DB."""

    entry: dict[str, object] = {"code": code, "summary": summary}
    if memory_extra:
        entry.update(memory_extra)
    error_logs.append(entry)
    writer = error_log_writer
    if writer is None or batch_run_id is None:
        return
    writer.record_error(
        batch_run_id=batch_run_id,
        error_code=code,
        error_message=summary,
        detail=detail,
        trace_id=trace_id,
    )


def emit_api_call(
    *,
    api_call_logs: list[dict[str, object]],
    api_call_log_writer: ApiCallLogWriter | None,
    batch_run_id: str | None,
    trace_id: str | None,
    api_call_log_id: str,
    source_api: str,
    call_status: str,
    memory_entry: dict[str, object],
    source: str = "rakuten",
    request_params_json: dict[str, Any] | None = None,
    error_code: str | None = None,
    duration_ms: int | None = None,
) -> None:
    """Append in-memory api call log and optionally write ``api_call_log`` to DB."""

    api_call_logs.append(dict(memory_entry))
    writer = api_call_log_writer
    if writer is None or batch_run_id is None:
        return
    writer.record_call(
        api_call_log_id=api_call_log_id,
        batch_run_id=batch_run_id,
        source=source,
        source_api=source_api,
        call_status=call_status,
        request_params_json=request_params_json,
        error_code=error_code,
        duration_ms=duration_ms,
        trace_id=trace_id,
    )
