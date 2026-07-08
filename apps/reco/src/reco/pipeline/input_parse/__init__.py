"""Input parse phase scaffold."""

from __future__ import annotations

from reco.domain.recommendation.request import RecommendationRequest
from reco.pipeline.context import PipelineContext


class InputParseStep:
    """Phase4a scaffold: attach typed RecommendationRequest to pipeline context."""

    phase = "input_parse"

    def execute(self, context: PipelineContext) -> PipelineContext:
        if context.recommendation_request is None and context.recommendation_request_id is not None:
            context.recommendation_request = RecommendationRequest(
                request_id=context.recommendation_request_id,
            )

        context.completed_phases.append(self.phase)
        return context
