"""MOD-RECO-024 Error Log write models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ErrorLogWriteRequest:
    """Request payload delegated to MOD-RECO-029 Error Log Writer."""

    trace_id: str
    owner_type: str
    owner_id: str | None
    service: str
    error_code: str
    error_message: str
    severity: str
    retryable: bool
    request_id: str | None = None
    error_detail_json: dict[str, object] = field(default_factory=dict)
