"""Batch job execution context passed between application phases."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BatchJobContext:
    """Mutable state container for a single batch job run."""

    batch_id: str | None = None
    job_run_id: str | None = None
    trace_id: str | None = None
    completed_phases: list[str] = field(default_factory=list)
    collected_records: list[dict[str, object]] | None = None
    transformed_records: list[dict[str, object]] | None = None
    loaded_row_count: int | None = None
