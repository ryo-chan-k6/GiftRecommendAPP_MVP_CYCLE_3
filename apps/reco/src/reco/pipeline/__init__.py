"""Reco recommendation pipeline scaffold (Phase4a)."""

from reco.pipeline.context import PipelineContext
from reco.pipeline.runner import PipelineRunner
from reco.pipeline.stages import DEFAULT_PIPELINE_STEPS, PIPELINE_PHASE_ORDER

__all__ = [
    "DEFAULT_PIPELINE_STEPS",
    "PIPELINE_PHASE_ORDER",
    "PipelineContext",
    "PipelineRunner",
]
