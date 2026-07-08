from reco.domain import (
    ExecutionCondition,
    ExecutionMode,
    PreferredCondition,
    RecommendationRequest,
    RelationshipCondition,
)
from reco.pipeline import PIPELINE_PHASE_ORDER, PipelineContext, PipelineRunner


def test_default_pipeline_runs_all_phases_in_order() -> None:
    context = PipelineContext(
        recommendation_request_id="req-1",
        recommendation_run_id="run-1",
    )

    result = PipelineRunner().run(context)

    assert result.completed_phases == list(PIPELINE_PHASE_ORDER)


def test_pipeline_runner_accepts_custom_steps() -> None:
    from reco.pipeline._scaffold import ScaffoldPipelineStep

    context = PipelineContext()
    steps = (ScaffoldPipelineStep(phase="custom"),)

    result = PipelineRunner(steps=steps).run(context)

    assert result.completed_phases == ["custom"]


def test_input_parse_attaches_typed_recommendation_request() -> None:
    context = PipelineContext(
        recommendation_request_id="req-1",
        recommendation_run_id="run-1",
    )

    result = PipelineRunner().run(context)

    assert result.recommendation_request is not None
    assert result.recommendation_request.request_id == "req-1"


def test_pipeline_preserves_pre_parsed_recommendation_request() -> None:
    request = RecommendationRequest(
        request_id="req-2",
        relationship=RelationshipCondition(relationship_code="boss"),
        preferred_condition=PreferredCondition(preferred_text="上品なもの"),
        execution=ExecutionCondition(mode=ExecutionMode.UI, top_k=5),
    )
    context = PipelineContext(
        recommendation_request_id="req-2",
        recommendation_request=request,
    )

    result = PipelineRunner().run(context)

    assert result.recommendation_request is request
    assert result.recommendation_request.has_minimum_input() is True
