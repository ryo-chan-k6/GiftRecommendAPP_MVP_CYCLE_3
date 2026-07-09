"""Batch application step protocol."""

from __future__ import annotations

from typing import Protocol

from batch.application.context import BatchJobContext


class BatchStep(Protocol):
    """Single phase in a batch job application flow."""

    phase: str

    def execute(self, context: BatchJobContext) -> BatchJobContext:
        """Run this phase and return the updated context."""
