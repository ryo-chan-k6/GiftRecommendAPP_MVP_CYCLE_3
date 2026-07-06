"""ErrorLogWriteRequest validation (MOD-RECO-029 §8.2)."""

from __future__ import annotations

from reco.application.reco_error_handler.models import ErrorLogWriteRequest

from .constants import (
    ALLOWED_OWNER_TYPES,
    ALLOWED_SERVICES,
    ALLOWED_SEVERITIES,
    GRS_ERROR_CODE_PATTERN,
)


class ErrorLogValidationError(ValueError):
    """Invalid Error Log write request."""


def validate_write_request(request: ErrorLogWriteRequest) -> None:
    if not request.trace_id.strip():
        raise ErrorLogValidationError("trace_id is required")
    if not request.owner_type.strip():
        raise ErrorLogValidationError("owner_type is required")
    if request.owner_type not in ALLOWED_OWNER_TYPES:
        raise ErrorLogValidationError(f"unsupported owner_type: {request.owner_type}")
    if not request.service.strip():
        raise ErrorLogValidationError("service is required")
    if request.service not in ALLOWED_SERVICES:
        raise ErrorLogValidationError(f"unsupported service: {request.service}")
    if not request.error_code.strip():
        raise ErrorLogValidationError("error_code is required")
    if GRS_ERROR_CODE_PATTERN.fullmatch(request.error_code) is None:
        raise ErrorLogValidationError(f"invalid error_code format: {request.error_code}")
    if not request.error_message.strip():
        raise ErrorLogValidationError("error_message is required")
    if request.severity not in ALLOWED_SEVERITIES:
        raise ErrorLogValidationError(f"unsupported severity: {request.severity}")

    if request.owner_type == "system":
        if request.owner_id is not None:
            raise ErrorLogValidationError("owner_id must be null when owner_type is system")
    elif not request.owner_id or not str(request.owner_id).strip():
        raise ErrorLogValidationError("owner_id is required for non-system owner_type")
