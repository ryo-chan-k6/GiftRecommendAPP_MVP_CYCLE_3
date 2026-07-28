"""Unit tests for Wave 4 batch observability apply (mapping + wiring samples)."""

from __future__ import annotations

from uuid import uuid4

from batch.application.import_summary.job import ImportSummaryJob
from batch.application.import_summary.models import (
    ApiCallLogRow,
    BatchRunLogRow,
    FeatureEmbeddingProgress,
    ProductDiffRow,
    SkipFailCounts,
)
from batch.application.import_summary.repositories import ImportSummaryRepositories
from batch.application.job_run import ScaffoldJobRunTracker
from batch.application.observability import (
    DEFAULT_APP_PHASE_TO_DDL,
    ALLOWED_BATCH_PHASE_NAMES,
    PostgresApiCallLogWriter,
    PostgresErrorLogWriter,
    PostgresPhaseLogWriter,
    map_app_phase_to_ddl,
)
from batch.application.ranking_snapshot.repositories import RankingSnapshotRepositories
from batch.application.raw_staging.repositories import RawStagingRepositories
from batch.infrastructure.db import ScaffoldDbWriter
from batch.infrastructure.object_storage import ScaffoldObjectStorageClient


def test_default_mapping_plan_finalize_and_identity() -> None:
    assert map_app_phase_to_ddl("plan") == "batch_started"
    assert map_app_phase_to_ddl("finalize") == "batch_completed"
    for name in ALLOWED_BATCH_PHASE_NAMES:
        assert map_app_phase_to_ddl(name) == name
        assert DEFAULT_APP_PHASE_TO_DDL[name] == name
    assert map_app_phase_to_ddl("fetch") is None
    assert map_app_phase_to_ddl("open_run") is None


def test_ranking_snapshot_wiring_writes_phase_error_api() -> None:
    db = ScaffoldDbWriter()
    repos = RankingSnapshotRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=db,
        bucket="scaffold-raw",
        phase_log_writer=PostgresPhaseLogWriter(db_writer=db),
        error_log_writer=PostgresErrorLogWriter(db_writer=db),
        api_call_log_writer=PostgresApiCallLogWriter(db_writer=db),
    )
    run_id = str(uuid4())
    api_id = str(uuid4())
    repos.bind_run(batch_run_id=run_id)

    repos.record_phase(phase="plan", status="succeeded")
    repos.record_phase(phase="fetch", status="succeeded")  # unmapped
    repos.record_error(code="GRS-BAT-001", summary="boom", genre_id="100")
    repos.record_api_call(
        api_call_log_id=api_id,
        genre_id="100",
        status="succeeded",
        period="daily",
        page=1,
    )

    phase_calls = [c for c in db.write_calls if c["table"] == "phase_log"]
    error_calls = [c for c in db.write_calls if c["table"] == "error_log"]
    api_calls = [c for c in db.write_calls if c["table"] == "api_call_log"]
    assert len(phase_calls) == 1
    assert phase_calls[0]["rows"][0]["phase_name"] == "batch_started"
    assert len(error_calls) == 1
    assert len(api_calls) == 1
    assert api_calls[0]["rows"][0]["source_api"] == "item_ranking"
    params = api_calls[0]["rows"][0]["request_params_json"]
    if hasattr(params, "obj"):
        params = params.obj
    assert params == {"genre_id": "100", "period": "daily", "page": 1}


def test_raw_staging_wiring_writes_phase_error_without_api() -> None:
    db = ScaffoldDbWriter()
    repos = RawStagingRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=db,
        bucket="scaffold-raw",
        phase_log_writer=PostgresPhaseLogWriter(db_writer=db),
        error_log_writer=PostgresErrorLogWriter(db_writer=db),
    )
    run_id = str(uuid4())
    repos.bind_run(batch_run_id=run_id)
    repos.record_phase(phase="plan", status="succeeded")
    repos.record_phase(phase="finalize", status="succeeded")
    repos.record_error(code="GRS-BAT-001", summary="x", raw_metadata_id="rm1")

    assert len([c for c in db.write_calls if c["table"] == "phase_log"]) == 2
    assert len([c for c in db.write_calls if c["table"] == "error_log"]) == 1
    assert not any(c["table"] == "api_call_log" for c in db.write_calls)


def test_import_summary_tracker_uses_job_run_id_not_aggregate_batch_run() -> None:
    """tracker.start は job_run_id、集計 / summary は別 batch_run_id。"""

    aggregate_id = "aggregate-run-017"
    job_run_id = str(uuid4())
    db = ScaffoldDbWriter()
    repos = ImportSummaryRepositories(
        db_writer=db,
        seed_batch_runs=[BatchRunLogRow(batch_run_id=aggregate_id, status="succeeded")],
        seed_api_calls=[
            ApiCallLogRow(
                batch_run_id=aggregate_id, source_api="item_search", item_count=2
            ),
        ],
        seed_diffs=[
            ProductDiffRow(
                batch_run_id=aggregate_id, source_api="item_search", diff_status="new"
            ),
        ],
        seed_skip_fail=SkipFailCounts(),
        seed_feature_embedding=FeatureEmbeddingProgress(),
        seed_default_source_api="item_search",
        phase_log_writer=PostgresPhaseLogWriter(db_writer=db),
        error_log_writer=PostgresErrorLogWriter(db_writer=db),
    )
    tracker = ScaffoldJobRunTracker()
    job = ImportSummaryJob(repositories=repos, job_run_tracker=tracker)
    repos.bind_run(batch_run_id=job_run_id)

    result = job.run(
        job_run_id=job_run_id,
        batch_run_id=aggregate_id,
        source_api="item_search",
    )

    assert result.status == "succeeded"
    assert result.job_run_id == job_run_id
    assert result.summary_row is not None
    assert result.summary_row.batch_run_id == aggregate_id

    starts = [r for r in tracker.records if r.status == "running"]
    assert len(starts) == 1
    assert starts[0].job_run_id == job_run_id
    assert starts[0].job_run_id != aggregate_id

    phase_calls = [c for c in db.write_calls if c["table"] == "phase_log"]
    assert phase_calls
    assert phase_calls[0]["rows"][0]["owner_id"] == job_run_id
    assert phase_calls[0]["rows"][0]["phase_name"] == "summary_created"
