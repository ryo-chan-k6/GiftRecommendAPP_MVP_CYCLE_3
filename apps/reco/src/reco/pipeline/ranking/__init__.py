"""Ranking phase scaffold."""

from reco.pipeline._scaffold import ScaffoldPipelineStep


class RankingStep(ScaffoldPipelineStep):
    def __init__(self) -> None:
        super().__init__(phase="ranking")
