"""Shared reco domain error protocol (MOD-RECO-024 §8.3.4)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class RecoDomainError(Protocol):
    """Structured exception contract for reco downstream modules."""

    error_code: str
    detail_error_code: str | None
    phase_name: str | None
