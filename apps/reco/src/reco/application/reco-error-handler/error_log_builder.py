"""Error Log request builder (MOD-RECO-024 §9)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .constants import (
    DEFAULT_RETRYABLE,
    DEFAULT_SEVERITY,
    SERVICE_NAME,
    SURFACE_CODE_METADATA,
)
from .message_masker import mask_sensitive_text
from .models import ErrorLogWriteRequest

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


def resolve_owner(context: ExecutionContext) -> tuple[str, str | None]:
    run_id = context.run_id
    if run_id:
        return "recommendation_run", run_id
    request_id = context.recommendation_request.request_id
    return "recommendation_request", request_id


def resolve_metadata(surface_code: str) -> tuple[str, bool]:
    metadata = SURFACE_CODE_METADATA.get(surface_code, {})
    severity = str(metadata.get("severity", DEFAULT_SEVERITY))
    retryable = bool(metadata.get("retryable", DEFAULT_RETRYABLE))
    return severity, retryable


def build_error_log_write_request(
    context: ExecutionContext,
    *,
    surface_code: str,
    detail_error_code: str | None,
    module_id: str,
    message: str,
    phase_name: str | None,
) -> ErrorLogWriteRequest:
    owner_type, owner_id = resolve_owner(context)
    severity, retryable = resolve_metadata(surface_code)
    masked_message = mask_sensitive_text(message)

    error_detail_json: dict[str, object] = {
        "source_module_id": module_id,
    }
    if phase_name:
        error_detail_json["phase_name"] = phase_name
    if detail_error_code:
        error_detail_json["detail_error_code"] = detail_error_code

    return ErrorLogWriteRequest(
        trace_id=context.trace_id,
        request_id=context.recommendation_request.request_id,
        owner_type=owner_type,
        owner_id=owner_id,
        service=SERVICE_NAME,
        error_code=surface_code,
        error_message=masked_message,
        severity=severity,
        retryable=retryable,
        error_detail_json=error_detail_json,
    )


def build_test_seam_event(request: ErrorLogWriteRequest) -> dict[str, object]:
    return {
        "trace_id": request.trace_id,
        "request_id": request.request_id,
        "owner_type": request.owner_type,
        "owner_id": request.owner_id,
        "service": request.service,
        "error_code": request.error_code,
        "error_message": request.error_message,
        "severity": request.severity,
        "retryable": request.retryable,
        "error_detail_json": dict(request.error_detail_json),
        "module_id": request.error_detail_json.get("source_module_id"),
        "phase_name": request.error_detail_json.get("phase_name"),
    }
