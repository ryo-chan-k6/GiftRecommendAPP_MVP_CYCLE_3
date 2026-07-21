"""In-memory Error Log repository for scaffold and unit tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from .models import ErrorLogRecord


@dataclass
class InMemoryErrorLogRepository:
    """Phase4a in-memory error_log store."""

    records: list[ErrorLogRecord] = field(default_factory=list)
    should_fail_on_insert: bool = False

    def insert(self, record: ErrorLogRecord) -> str:
        if self.should_fail_on_insert:
            raise RuntimeError("error_log insert failed")

        self.records.append(record)
        return str(uuid4())
