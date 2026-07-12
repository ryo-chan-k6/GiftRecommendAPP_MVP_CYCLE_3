"""Matching phase scaffold."""

from reco.pipeline._scaffold import ScaffoldPipelineStep


class MatchingStep(ScaffoldPipelineStep):
    def __init__(self) -> None:
        super().__init__(phase="matching")
