"""Shared scaffold helpers for pipeline phase modules."""

from __future__ import annotations

from dataclasses import dataclass

from reco.pipeline.context import PipelineContext


@dataclass(frozen=True)
class ScaffoldPipelineStep:
    """Phase4a placeholder step that records completion without domain logic."""

    phase: str

    def execute(self, context: PipelineContext) -> PipelineContext:
        context.completed_phases.append(self.phase)
        return context
