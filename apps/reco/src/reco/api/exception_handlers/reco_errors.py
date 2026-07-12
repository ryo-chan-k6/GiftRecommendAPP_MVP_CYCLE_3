"""Exception handlers: Validation / RecoError → HTTP + GRS-*."""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from reco.api.errors import ErrorDetail, RecoApiError, default_message, reco_error_from_code
from reco.api.metrics.health_metrics import record_reco_health_check
from reco.api.middleware.trace_context import HEADER_REQUEST_ID, HEADER_TRACE_ID
from reco.application.recommendation_orchestrator.errors import RecoError

_RECO_HEALTH_PATH = "/internal/reco/v1/health"


def _is_reco_health_path(request: Request) -> bool:
    return request.url.path.rstrip("/") == _RECO_HEALTH_PATH


def _meta_from_request(request: Request) -> dict[str, str]:
    trace_id = (request.headers.get(HEADER_TRACE_ID) or "").strip()
    request_id = (request.headers.get(HEADER_REQUEST_ID) or "").strip()
    # API-INT-001: Trace/Request は任意。未指定時はサーバ採番可（実装仕様書 §4.2）
    if _is_reco_health_path(request):
        trace_id = trace_id or str(uuid.uuid4())
        request_id = request_id or f"req_{uuid.uuid4().hex[:12]}"
    return {
        "traceId": trace_id,
        "requestId": request_id,
    }


def _error_envelope(
    *,
    status_code: int,
    error_code: str,
    message: str,
    meta: dict[str, str],
    details: list[ErrorDetail] | None = None,
) -> JSONResponse:
    body: dict[str, object] = {
        "error": {
            "code": error_code,
            "message": message,
        },
        "meta": meta,
    }
    if details:
        body["error"]["details"] = [
            {"field": detail.field, "message": detail.message} for detail in details
        ]
    return JSONResponse(status_code=status_code, content=body)


async def handle_reco_api_error(request: Request, exc: RecoApiError) -> JSONResponse:
    meta = _meta_from_request(request)
    if _is_reco_health_path(request) and exc.error_code.startswith("GRS-AUTH-"):
        record_reco_health_check(
            result="auth_error",
            http_status=exc.status_code,
            trace_id=meta.get("traceId") or None,
            request_id=meta.get("requestId") or None,
        )
    return _error_envelope(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        meta=meta,
        details=exc.details,
    )


async def handle_request_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details = [
        ErrorDetail(
            field=".".join(str(part) for part in error.get("loc", ())),
            message=str(error.get("msg", "invalid value")),
        )
        for error in exc.errors()
    ]
    api_error = reco_error_from_code(
        "GRS-REQ-001",
        message="リクエスト形式が不正です。",
        details=details,
    )
    return await handle_reco_api_error(request, api_error)


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    api_error = reco_error_from_code("GRS-REC-999", message=default_message("GRS-REC-999"))
    return await handle_reco_api_error(request, api_error)


def map_reco_error(reco_error: RecoError) -> RecoApiError:
    return reco_error_from_code(
        reco_error.error_code,
        message=reco_error.message or default_message(reco_error.error_code),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RecoApiError, handle_reco_api_error)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
