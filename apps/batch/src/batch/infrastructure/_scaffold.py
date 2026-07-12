"""Shared scaffold helpers for infrastructure modules."""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def scaffold_placeholder(*, module: str, concept: str) -> None:
    """Mark a Phase4a infrastructure module as scaffold-only."""

    _ = (module, concept)
