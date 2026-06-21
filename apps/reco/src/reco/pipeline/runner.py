"""Pipeline orchestration."""

from __future__ import annotations

from collections.abc import Sequence

from reco.pipeline.context import PipelineContext
from reco.pipeline.stages import DEFAULT_PIPELINE_STEPS
from reco.pipeline.step import PipelineStep


class PipelineRunner:
    """Executes recommendation pipeline phases in order."""

    def __init__(self, steps: Sequence[PipelineStep] | None = None) -> None:
        self._steps = list(steps if steps is not None else DEFAULT_PIPELINE_STEPS)

    @property
    def steps(self) -> tuple[PipelineStep, ...]:
        return tuple(self._steps)

    def run(self, context: PipelineContext) -> PipelineContext:
        current = context
        for step in self._steps:
            current = step.execute(current)
        return current
