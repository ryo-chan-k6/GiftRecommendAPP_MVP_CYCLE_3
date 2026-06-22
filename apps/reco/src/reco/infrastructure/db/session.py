"""Database session scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DatabaseHealth:
    """Health probe result for a database session."""

    is_available: bool
    backend: str


class DatabaseSession(Protocol):
    """Database access boundary (Phase4a protocol)."""

    def health_check(self) -> DatabaseHealth: ...


@dataclass
class ScaffoldDatabaseSession:
    """Phase4a placeholder session without a real database connection."""

    backend: str = "scaffold"
    is_available: bool = True

    def health_check(self) -> DatabaseHealth:
        return DatabaseHealth(is_available=self.is_available, backend=self.backend)
