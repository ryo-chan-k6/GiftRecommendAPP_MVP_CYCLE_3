"""Default pipeline stage wiring."""

from __future__ import annotations

from reco.pipeline.input_parse import InputParseStep
from reco.pipeline.matching import MatchingStep
from reco.pipeline.ranking import RankingStep
from reco.pipeline.reason import ReasonStep
from reco.pipeline.retrieval import RetrievalStep
from reco.pipeline.step import PipelineStep
from reco.pipeline.user_feature import UserFeatureStep

PIPELINE_PHASE_ORDER: tuple[str, ...] = (
    "input_parse",
    "user_feature",
    "retrieval",
    "matching",
    "ranking",
    "reason",
)

DEFAULT_PIPELINE_STEPS: tuple[PipelineStep, ...] = (
    InputParseStep(),
    UserFeatureStep(),
    RetrievalStep(),
    MatchingStep(),
    RankingStep(),
    ReasonStep(),
)
