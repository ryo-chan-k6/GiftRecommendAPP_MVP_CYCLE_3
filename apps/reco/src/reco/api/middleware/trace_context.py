"""Trace / request header context for API-INT-002."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Header, Request

from reco.api.errors import ErrorDetail, reco_error_from_code

HEADER_TRACE_ID = "X-Trace-Id"
HEADER_REQUEST_ID = "X-Request-Id"


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    request_id: str


def _require_non_empty(value: str | None, field_name: str) -> str:
    if value is None or value.strip() == "":
        raise reco_error_from_code(
            "GRS-REQ-001",
            message="追跡 ID が不正です。",
            details=[ErrorDetail(field=field_name, message="必須項目です。")],
        )
    return value.strip()


def require_trace_context(
    x_trace_id: Annotated[str | None, Header(alias=HEADER_TRACE_ID)] = None,
    x_request_id: Annotated[str | None, Header(alias=HEADER_REQUEST_ID)] = None,
) -> TraceContext:
    return TraceContext(
        trace_id=_require_non_empty(x_trace_id, HEADER_TRACE_ID),
        request_id=_require_non_empty(x_request_id, HEADER_REQUEST_ID),
    )


def require_json_headers(request: Request) -> None:
    content_type = request.headers.get("content-type", "")
    if not content_type.lower().startswith("application/json"):
        raise reco_error_from_code(
            "GRS-REQ-001",
            message="リクエスト形式が不正です。",
            details=[ErrorDetail(field="Content-Type", message="application/json が必要です。")],
        )
    accept = request.headers.get("accept", "application/json")
    if accept != "*/*" and "application/json" not in accept.lower():
        raise reco_error_from_code(
            "GRS-REQ-001",
            message="リクエスト形式が不正です。",
            details=[ErrorDetail(field="Accept", message="application/json が必要です。")],
        )
