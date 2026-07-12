"""Shared scaffold helpers for domain modules."""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def scaffold_placeholder(*, module: str, concept: str) -> None:
    """Mark a Phase4a module as scaffold-only without domain logic."""

    _ = (module, concept)
