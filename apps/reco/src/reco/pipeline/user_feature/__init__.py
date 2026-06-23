"""User feature generation phase scaffold."""

from reco.pipeline._scaffold import ScaffoldPipelineStep


class UserFeatureStep(ScaffoldPipelineStep):
    def __init__(self) -> None:
        super().__init__(phase="user_feature")
