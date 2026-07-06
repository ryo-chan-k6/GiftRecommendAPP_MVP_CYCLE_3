"""MOD-RECO-024 downstream ports."""

from __future__ import annotations

from typing import Protocol

from .models import ErrorLogWriteRequest


class ErrorLogWriterPort(Protocol):
    """Persistence boundary for MOD-RECO-029 Error Log Writer."""

    module_id: str

    def write(self, request: ErrorLogWriteRequest) -> None: ...
