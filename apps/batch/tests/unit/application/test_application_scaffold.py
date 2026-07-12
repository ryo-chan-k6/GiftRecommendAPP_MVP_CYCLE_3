from batch.application import (
    BATCH_PHASE_ORDER,
    BatchJobContext,
    BatchJobRunner,
    ScaffoldJobRunTracker,
)
from batch.application._scaffold import ScaffoldBatchStep
from batch.infrastructure.rakuten import RakutenItem, ScaffoldRakutenApiClient


def test_default_batch_job_runs_all_phases_in_order() -> None:
    context = BatchJobContext(
        batch_id="BATCH-003",
        job_run_id="job-1",
        trace_id="trace-1",
    )

    result = BatchJobRunner().run(context)

    assert result.completed_phases == list(BATCH_PHASE_ORDER)


def test_batch_job_runner_accepts_custom_steps() -> None:
    context = BatchJobContext()
    steps = (ScaffoldBatchStep(phase="custom"),)

    result = BatchJobRunner(steps=steps).run(context)

    assert result.completed_phases == ["custom"]


def test_collector_transformer_loader_pipeline_records_scaffold_outputs() -> None:
    rakuten_client = ScaffoldRakutenApiClient(
        items=(RakutenItem(item_code="item-1", item_name="Gift Box"),),
    )
    context = BatchJobContext(batch_id="BATCH-003", job_run_id="job-2")

    from batch.application.collector import CollectorStep
    from batch.application.loader import LoaderStep
    from batch.application.transformer import TransformerStep

    result = BatchJobRunner(
        steps=(
            CollectorStep(rakuten_client=rakuten_client),
            TransformerStep(),
            LoaderStep(),
        )
    ).run(context)

    assert result.collected_records == [{"item_code": "item-1", "item_name": "Gift Box"}]
    assert result.transformed_records == [
        {
            "item_code": "item-1",
            "normalized_name": "Gift Box",
            "source_phase": "transformer",
        }
    ]
    assert result.loaded_row_count == 1


def test_scaffold_job_run_tracker_records_lifecycle() -> None:
    tracker = ScaffoldJobRunTracker()

    started = tracker.start(batch_id="BATCH-003", job_run_id="job-3")
    completed = tracker.complete(batch_id="BATCH-003", job_run_id="job-3", status="succeeded")

    assert started.status == "running"
    assert completed.status == "succeeded"
    assert len(tracker.records) == 2
