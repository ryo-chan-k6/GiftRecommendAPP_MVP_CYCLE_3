"""Database writer scaffold for batch loaders."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class DbWriteResult:
    """Result of a batch write operation."""

    rows_affected: int
    table: str


class DbWriter(Protocol):
    """Database write boundary for batch loaders (Phase4a protocol)."""

    def write_rows(self, table: str, rows: tuple[dict[str, object], ...]) -> DbWriteResult: ...


@dataclass
class ScaffoldDbWriter:
    """Phase4a placeholder writer without a real database connection."""

    write_calls: list[dict[str, object]] = field(default_factory=list)

    def write_rows(self, table: str, rows: tuple[dict[str, object], ...]) -> DbWriteResult:
        self.write_calls.append({"table": table, "rows": rows})
        return DbWriteResult(rows_affected=len(rows), table=table)
