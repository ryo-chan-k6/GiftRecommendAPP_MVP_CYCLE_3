"""Default batch application stage wiring."""

from __future__ import annotations

from batch.application.collector import CollectorStep
from batch.application.loader import LoaderStep
from batch.application.step import BatchStep
from batch.application.transformer import TransformerStep

BATCH_PHASE_ORDER: tuple[str, ...] = (
    "collector",
    "transformer",
    "loader",
)

DEFAULT_BATCH_STEPS: tuple[BatchStep, ...] = (
    CollectorStep(),
    TransformerStep(),
    LoaderStep(),
)
