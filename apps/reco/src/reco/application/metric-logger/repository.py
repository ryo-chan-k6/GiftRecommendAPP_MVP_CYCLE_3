"""In-memory Metric repository for scaffold and unit tests."""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import MetricRecord


@dataclass
class InMemoryMetricLoggerRepository:
    """Phase4a in-memory metric store."""

    records: list[MetricRecord] = field(default_factory=list)
    should_fail_on_save: bool = False

    def save(self, record: MetricRecord) -> None:
        if self.should_fail_on_save:
            raise RuntimeError("metric_log save failed")

        self.records.append(record)
