"""Internal API Key authentication (X-Internal-Api-Key / RECO_INTERNAL_API_KEY)."""

from __future__ import annotations

import hmac
import os
from typing import Annotated

from fastapi import Header

from reco.api.errors import RecoApiError, reco_error_from_code

ENV_INTERNAL_API_KEY = "RECO_INTERNAL_API_KEY"
HEADER_INTERNAL_API_KEY = "X-Internal-Api-Key"


def verify_internal_api_key(provided_key: str | None) -> None:
    """定数時間比較で Internal API Key を検証する。Secret はログに出さない。"""
    expected = os.environ.get(ENV_INTERNAL_API_KEY)
    if expected is None or expected.strip() == "":
        raise reco_error_from_code("GRS-AUTH-004")
    if provided_key is None or provided_key.strip() == "":
        raise reco_error_from_code("GRS-AUTH-004")
    if not hmac.compare_digest(provided_key, expected):
        raise reco_error_from_code("GRS-AUTH-001")


def require_internal_api_key(
    x_internal_api_key: Annotated[str | None, Header(alias=HEADER_INTERNAL_API_KEY)] = None,
) -> None:
    verify_internal_api_key(x_internal_api_key)
