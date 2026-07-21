"""MOD-RECO-028 repository port."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .models import PhaseLogRecord


class PhaseLogRepository(Protocol):
    """Persistence boundary for phase_log."""

    def insert_started(self, record: PhaseLogRecord) -> str: ...

    def update_terminal(
        self,
        phase_log_id: str,
        *,
        phase_status: str,
        completed_at: datetime,
        duration_ms: int | None,
        error_code: str | None,
        detail_json: dict[str, object],
    ) -> None: ...
