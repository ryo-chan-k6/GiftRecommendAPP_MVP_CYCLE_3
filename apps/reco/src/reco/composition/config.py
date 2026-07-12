"""Composition mode and database URL resolution."""

from __future__ import annotations

import os
from enum import StrEnum


class CompositionMode(StrEnum):
    """Orchestrator composition selection."""

    DEFAULT = "default"
    PRODUCTION = "production"


def resolve_database_url(explicit: str | None = None) -> str | None:
    """Resolve ``DATABASE_URL`` without logging secret values."""

    if explicit is not None:
        return explicit
    return os.environ.get("DATABASE_URL")
