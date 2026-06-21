"""Pipeline step protocol."""

from __future__ import annotations

from typing import Protocol

from reco.pipeline.context import PipelineContext


class PipelineStep(Protocol):
    """Single phase in the recommendation pipeline."""

    phase: str

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Run this phase and return the updated context."""
