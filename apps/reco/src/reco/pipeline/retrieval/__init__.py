"""Retrieval phase scaffold."""

from reco.pipeline._scaffold import ScaffoldPipelineStep


class RetrievalStep(ScaffoldPipelineStep):
    def __init__(self) -> None:
        super().__init__(phase="retrieval")
