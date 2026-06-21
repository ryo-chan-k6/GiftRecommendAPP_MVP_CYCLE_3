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
