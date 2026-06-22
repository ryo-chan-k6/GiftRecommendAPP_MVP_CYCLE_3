"""Reco logger scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from reco.infrastructure.logger.context import LogContext


@dataclass(frozen=True)
class LogRecord:
    """Captured log entry for scaffold testing."""

    level: str
    event: str
    context: LogContext
    attributes: dict[str, object]


class RecoLogger(Protocol):
    """Structured logging boundary (Phase4a protocol)."""

    def bind(self, **kwargs: str) -> RecoLogger: ...

    def info(self, event: str, **attributes: object) -> None: ...

    def error(self, event: str, **attributes: object) -> None: ...


@dataclass
class ScaffoldRecoLogger:
    """Phase4a in-memory logger for unit tests and pipeline tracing."""

    context: LogContext = field(default_factory=LogContext)
    records: list[LogRecord] = field(default_factory=list)

    def bind(self, **kwargs: str) -> ScaffoldRecoLogger:
        merged = LogContext(
            trace_id=kwargs.get("trace_id", self.context.trace_id),
            run_id=kwargs.get("run_id", self.context.run_id),
        )
        return ScaffoldRecoLogger(context=merged, records=self.records)

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
