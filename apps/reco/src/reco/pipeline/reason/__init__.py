"""Reason generation phase scaffold."""

from reco.pipeline._scaffold import ScaffoldPipelineStep


class ReasonStep(ScaffoldPipelineStep):
    def __init__(self) -> None:
        super().__init__(phase="reason")
