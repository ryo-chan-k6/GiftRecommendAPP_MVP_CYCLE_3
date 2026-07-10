"""GET /internal/reco/v1/health route (API-INT-001)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from reco.api.auth.internal_api_key import require_internal_api_key
from reco.api.errors import reco_error_from_code
from reco.api.middleware.trace_context import HEADER_REQUEST_ID, HEADER_TRACE_ID
from reco.config.loader import load_reco_settings
from reco.infrastructure.db.session import PostgresDatabaseSession, ScaffoldDatabaseSession

router = APIRouter(prefix="/internal/reco/v1", tags=["RecoHealth"])


def _resolve_trace_meta(
    *,
    x_trace_id: str | None,
    x_request_id: str | None,
) -> dict[str, str]:
    """health は Trace/Request 任意。未指定時はサーバ側で採番する。"""
    trace_id = (x_trace_id or "").strip() or str(uuid.uuid4())
    request_id = (x_request_id or "").strip() or f"req_{uuid.uuid4().hex[:12]}"
    return {"traceId": trace_id, "requestId": request_id}


def _probe_database() -> bool:
    settings = load_reco_settings()
    if settings.database_url is None or settings.database_url.strip() == "":
        # DATABASE_URL 未設定時は scaffold でプロセス稼働のみ確認（ローカル最小）
        return ScaffoldDatabaseSession().health_check().is_available
    return PostgresDatabaseSession(database_url=settings.database_url).health_check().is_available


@router.get(
    "/health",
    response_model=None,
    summary="Recoヘルスチェック（API-INT-001）",
)
async def get_reco_health(
    _auth: None = Depends(require_internal_api_key),
    x_trace_id: Annotated[str | None, Header(alias=HEADER_TRACE_ID)] = None,
    x_request_id: Annotated[str | None, Header(alias=HEADER_REQUEST_ID)] = None,
) -> JSONResponse:
    meta = _resolve_trace_meta(x_trace_id=x_trace_id, x_request_id=x_request_id)
    checked_at = datetime.now(tz=UTC).isoformat()

    if not _probe_database():
        # OpenAPI: unavailable は HTTP 503 + ErrorResponse
        raise reco_error_from_code("GRS-COM-003")

    return JSONResponse(
        status_code=200,
        content={
            "data": {
                "status": "ok",
                "service": "reco",
                "version": "0.1.0",
                "checkedAt": checked_at,
            },
            "meta": {
                **meta,
                "generatedAt": checked_at,
            },
        },
    )
