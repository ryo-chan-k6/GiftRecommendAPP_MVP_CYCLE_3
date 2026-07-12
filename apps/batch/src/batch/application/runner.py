"""Batch job application orchestration."""

from __future__ import annotations

from collections.abc import Sequence

from batch.application.context import BatchJobContext
from batch.application.stages import DEFAULT_BATCH_STEPS
from batch.application.step import BatchStep


class BatchJobRunner:
    """Executes collector / transformer / loader phases in order."""

    def __init__(self, steps: Sequence[BatchStep] | None = None) -> None:
        self._steps = list(steps if steps is not None else DEFAULT_BATCH_STEPS)

    @property
    def steps(self) -> tuple[BatchStep, ...]:
        return tuple(self._steps)

    def run(self, context: BatchJobContext) -> BatchJobContext:
        current = context
        for step in self._steps:
            current = step.execute(current)
        return current
