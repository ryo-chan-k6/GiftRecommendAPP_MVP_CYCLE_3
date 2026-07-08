"""Batch logger scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from batch.infrastructure.logger.context import LogContext


@dataclass(frozen=True)
class LogRecord:
    """Captured log entry for scaffold testing."""

    level: str
    event: str
    context: LogContext
    attributes: dict[str, object]


class BatchLogger(Protocol):
    """Structured logging boundary for batch jobs (Phase4a protocol)."""

    def bind(self, **kwargs: str) -> BatchLogger: ...

    def info(self, event: str, **attributes: object) -> None: ...

    def error(self, event: str, **attributes: object) -> None: ...


@dataclass
class ScaffoldBatchLogger:
    """Phase4a in-memory logger for unit tests and job tracing."""

    context: LogContext = field(default_factory=LogContext)
    records: list[LogRecord] = field(default_factory=list)

    def bind(self, **kwargs: str) -> ScaffoldBatchLogger:
        merged = LogContext(
            trace_id=kwargs.get("trace_id", self.context.trace_id),
            job_run_id=kwargs.get("job_run_id", self.context.job_run_id),
        )
        return ScaffoldBatchLogger(context=merged, records=self.records)

    def info(self, event: str, **attributes: object) -> None:
        self._append("info", event, attributes)

    def error(self, event: str, **attributes: object) -> None:
        self._append("error", event, attributes)

    def _append(self, level: str, event: str, attributes: dict[str, object]) -> None:
        self.records.append(
            LogRecord(
                level=level,
                event=event,
                context=self.context,
                attributes=dict(attributes),
            )
        )
