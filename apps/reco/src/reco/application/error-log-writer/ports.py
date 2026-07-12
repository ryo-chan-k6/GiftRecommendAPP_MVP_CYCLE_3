"""MOD-RECO-029 repository port."""

from __future__ import annotations

from typing import Protocol

from .models import ErrorLogRecord


class ErrorLogRepository(Protocol):
    """Persistence boundary for error_log."""

    def insert(self, record: ErrorLogRecord) -> str: ...
