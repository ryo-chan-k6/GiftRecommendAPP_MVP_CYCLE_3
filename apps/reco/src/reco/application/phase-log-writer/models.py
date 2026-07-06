"""MOD-RECO-028 persistence models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class PhaseLogRecord:
    """Row snapshot for phase_log INSERT (started)."""

    trace_id: str | None
    owner_type: str
    owner_id: str
    phase_name: str
    phase_status: str
    started_at: datetime
    detail_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class BufferedPhaseEvent:
    """Event retained until recommendation_run_id is available."""

    phase_name: str
    phase_status: str
    module_id: str | None
    error_code: str | None
    duration_ms: int | None
