"""Input parse phase scaffold."""

from reco.pipeline._scaffold import ScaffoldPipelineStep


class InputParseStep(ScaffoldPipelineStep):
    def __init__(self) -> None:
        super().__init__(phase="input_parse")
