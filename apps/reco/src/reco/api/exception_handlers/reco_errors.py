"""Exception handlers: Validation / RecoError → HTTP + GRS-*."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from reco.api.errors import ErrorDetail, RecoApiError, default_message, reco_error_from_code
from reco.api.middleware.trace_context import HEADER_REQUEST_ID, HEADER_TRACE_ID
from reco.application.recommendation_orchestrator.errors import RecoError


def _meta_from_request(request: Request) -> dict[str, str]:
    trace_id = request.headers.get(HEADER_TRACE_ID, "")
    request_id = request.headers.get(HEADER_REQUEST_ID, "")
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
    return _error_envelope(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        meta=_meta_from_request(request),
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
