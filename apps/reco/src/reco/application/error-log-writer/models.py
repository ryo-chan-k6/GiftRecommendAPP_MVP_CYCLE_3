"""MOD-RECO-029 persistence models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ErrorLogRecord:
    """Row snapshot for error_log INSERT."""

    trace_id: str | None
    request_id: str | None
    owner_type: str
    owner_id: str | None
    service: str
    error_code: str
    error_message: str
    severity: str
    retryable: bool
    error_detail_json: dict[str, object]
    occurred_at: datetime
