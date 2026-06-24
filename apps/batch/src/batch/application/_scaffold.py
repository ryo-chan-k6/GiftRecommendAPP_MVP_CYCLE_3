"""Shared scaffold helpers for application modules."""

from __future__ import annotations

from dataclasses import dataclass

from batch.application.context import BatchJobContext


@dataclass(frozen=True)
class ScaffoldBatchStep:
    """Phase4a placeholder step that records completion without domain logic."""

    phase: str

    def execute(self, context: BatchJobContext) -> BatchJobContext:
        context.completed_phases.append(self.phase)
        return context
