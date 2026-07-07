"""MOD-RECO-025 repository port."""

from __future__ import annotations

from typing import Protocol

from .models import MetricRecord


class MetricLoggerRepository(Protocol):
    """Persistence boundary for Run-scoped Metric rows."""

    def save(self, record: MetricRecord) -> None: ...
