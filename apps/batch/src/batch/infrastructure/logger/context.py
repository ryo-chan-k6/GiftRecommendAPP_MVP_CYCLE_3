"""Logging context scaffold."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LogContext:
    """Correlation identifiers for batch observability."""

    trace_id: str | None = None
    job_run_id: str | None = None
