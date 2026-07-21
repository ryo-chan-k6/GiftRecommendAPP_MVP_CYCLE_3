"""ErrorLogWriteRequest to ErrorLogRecord mapping."""

from __future__ import annotations

from datetime import UTC, datetime

from reco.application.reco_error_handler.models import ErrorLogWriteRequest

from .models import ErrorLogRecord


def map_write_request_to_record(
    request: ErrorLogWriteRequest,
    *,
    occurred_at: datetime | None = None,
) -> ErrorLogRecord:
    timestamp = occurred_at or datetime.now(UTC)
    return ErrorLogRecord(
        trace_id=request.trace_id,
        request_id=request.request_id,
        owner_type=request.owner_type,
        owner_id=request.owner_id,
        service=request.service,
        error_code=request.error_code,
        error_message=request.error_message,
        severity=request.severity,
        retryable=request.retryable,
        error_detail_json=dict(request.error_detail_json),
        occurred_at=timestamp,
    )
