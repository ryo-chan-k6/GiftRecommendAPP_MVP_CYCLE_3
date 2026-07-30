"""GET /internal/reco/v1/health route (API-INT-001)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from reco.api.auth.internal_api_key import require_internal_api_key
from reco.api.errors import default_message
from reco.api.metrics.health_metrics import record_reco_health_check
from reco.api.middleware.trace_context import HEADER_REQUEST_ID, HEADER_TRACE_ID
from reco.config.loader import load_reco_settings
from reco.infrastructure.db.session import (
    DatabaseSession,
    PostgresDatabaseSession,
    ScaffoldDatabaseSession,
)

router = APIRouter(prefix="/internal/reco/v1", tags=["RecoHealth"])

SERVICE_NAME = "reco"
APP_VERSION = "0.1.0"
HEALTH_PATH_SUFFIX = "/internal/reco/v1/health"


def _resolve_trace_meta(
    *,
    x_trace_id: str | None,
    x_request_id: str | None,
) -> dict[str, str]:
    """health は Trace/Request 任意。未指定時はサーバ側で採番する。"""
    trace_id = (x_trace_id or "").strip() or str(uuid.uuid4())
    request_id = (x_request_id or "").strip() or f"req_{uuid.uuid4().hex[:12]}"
    return {"traceId": trace_id, "requestId": request_id}


def _probe_database(session: DatabaseSession | None = None) -> bool:
    """Probe DB via the shared lifespan session when available.

    Fallback: construct a short-lived session when app.state is not initialized
    (e.g. isolated unit calls). Prefer the shared pool in normal runtime.
    """
    if session is not None:
        return session.health_check().is_available

    settings = load_reco_settings()
    if settings.database_url is None or settings.database_url.strip() == "":
        # ローカル最小: DATABASE_URL 未設定時は scaffold でプロセス稼働のみ確認
        # （実装仕様書 §11 No.1 推奨。本番/staging では DATABASE_URL 必須想定）
        return ScaffoldDatabaseSession().health_check().is_available

    fallback = PostgresDatabaseSession(database_url=settings.database_url)
    try:
        fallback.open()
        return fallback.health_check().is_available
    finally:
        fallback.close()


def _error_response(
    *,
    status_code: int,
    error_code: str,
    meta: dict[str, str],
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code,
                "message": default_message(error_code),
            },
            "meta": meta,
        },
    )


@router.get(
    "/health",
    response_model=None,
    summary="Recoヘルスチェック（API-INT-001）",
)
async def get_reco_health(
    request: Request,
    _auth: None = Depends(require_internal_api_key),
    x_trace_id: Annotated[str | None, Header(alias=HEADER_TRACE_ID)] = None,
    x_request_id: Annotated[str | None, Header(alias=HEADER_REQUEST_ID)] = None,
) -> JSONResponse:
    meta = _resolve_trace_meta(x_trace_id=x_trace_id, x_request_id=x_request_id)
    checked_at = datetime.now(tz=UTC).isoformat()
    shared_session = getattr(request.app.state, "database_session", None)

    if not _probe_database(shared_session):
        # OpenAPI: 503 + ErrorResponse（data なし）
        record_reco_health_check(
            result="unavailable",
            http_status=503,
            trace_id=meta["traceId"],
            request_id=meta["requestId"],
        )
        return _error_response(status_code=503, error_code="GRS-COM-003", meta=meta)

    record_reco_health_check(
        result="ok",
        http_status=200,
        trace_id=meta["traceId"],
        request_id=meta["requestId"],
    )
    return JSONResponse(
        status_code=200,
        content={
            "data": {
                "status": "ok",
                "service": SERVICE_NAME,
                "version": APP_VERSION,
                "checkedAt": checked_at,
            },
            "meta": {
                **meta,
                "generatedAt": checked_at,
            },
        },
    )
