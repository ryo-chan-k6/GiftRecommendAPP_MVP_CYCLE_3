"""Unit tests for BATCH-018 Offline Evaluation（仕様書 §16 最小 / scaffold-first）.

fixture/mock のみ。実 DB / secret / HTTP に依存しない。
"""

from __future__ import annotations

from datetime import UTC, datetime

from batch.application.offline_evaluation import (
    BATCH_ID,
    MVP_METRIC_NAMES,
    OFFLINE_EVALUATION_PHASES,
    PHASE_EVALUATION_COMPLETED,
    DuplicateInsertError,
    EvaluationCaseRow,
    EvaluationDatasetRow,
    EvaluationResultRow,
    OfflineEvaluationJob,
    OfflineEvaluationRepositories,
    calculate_mvp_metrics,
    mrr_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from batch.application.offline_evaluation.__main__ import build_scaffold_demo_job, main
from batch.application.job_run import ScaffoldJobRunTracker
from batch.config import load_batch_settings, scaffold_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter
from batch.infrastructure.reco_client import MockRecoEvaluationClient

_NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=UTC)
_DS = "ds-018-1"
_CASE_1 = "case-018-1"
_CASE_2 = "case-018-2"


def _repos(
    *,
    active: bool = True,
    cases: list[EvaluationCaseRow] | None = None,
    include_dataset: bool = True,
) -> tuple[OfflineEvaluationRepositories, ScaffoldDbWriter]:
    db = ScaffoldDbWriter()
    datasets = (
        [
            EvaluationDatasetRow(
                evaluation_dataset_id=_DS,
                dataset_name="offline_eval_ut",
                dataset_version="v1",
                is_active=active,
            )
        ]
        if include_dataset
        else []
    )
    default_cases = [
        EvaluationCaseRow(
            evaluation_case_id=_CASE_1,
            evaluation_dataset_id=_DS,
            case_label="case_001",
            expected_result_json={"golden_item_ids": ["a", "b", "c"]},
            is_active=True,
        ),
        EvaluationCaseRow(
            evaluation_case_id=_CASE_2,
            evaluation_dataset_id=_DS,
            case_label="case_002",
            expected_result_json={"golden_item_ids": ["x", "y"]},
            is_active=True,
        ),
    ]
    repos = OfflineEvaluationRepositories(
        db_writer=db,
        seed_datasets=datasets,
        seed_cases=cases if cases is not None else default_cases,
    )
    return repos, db


def _run(
    repos: OfflineEvaluationRepositories,
    *,
    job_run_id: str = "run-018-1",
    reco: MockRecoEvaluationClient | None = None,
    tracker: ScaffoldJobRunTracker | None = None,
    max_cases: int | None = None,
    dry_run: bool = False,
):
    job = OfflineEvaluationJob(
        repositories=repos,
        reco_client=reco or MockRecoEvaluationClient(),
        job_run_tracker=tracker,
    )
    return job.run(
        job_run_id=job_run_id,
        evaluation_dataset_id=_DS,
        max_cases=max_cases,
        dry_run=dry_run,
        now=_NOW,
    )


def test_happy_path_inserts_run_result_metrics_and_phases() -> None:
    repos, db = _repos()
    result = _run(repos)

    assert result.batch_id == BATCH_ID
    assert result.status == "succeeded"
    assert result.cases_evaluated == 2
    assert result.results_inserted == 2
    assert result.metrics_inserted == 8  # 4 metrics × 2 cases
    assert result.evaluation_status == "succeeded"
    assert "open_run" in result.completed_phases
    assert "finalize" in result.completed_phases
    assert set(result.completed_phases) <= set(OFFLINE_EVALUATION_PHASES) | set(
        result.completed_phases
    )
    for phase in OFFLINE_EVALUATION_PHASES:
        assert phase in result.completed_phases

    assert len(repos.runs) == 1
    assert repos.runs[0].evaluation_status == "succeeded"
    assert repos.run_insert_count == 1
    assert repos.run_status_update_count >= 2  # running + succeeded
    assert repos.result_insert_count == 2
    assert repos.metric_insert_count == 8
    assert repos.result_update_count == 0
    assert repos.metric_update_count == 0
    assert repos.dataset_write_count == 0
    assert repos.case_write_count == 0
    assert repos.evaluation_run_log_write_count == 0
    assert result.http_call_count == 0

    tables = {call["table"] for call in db.write_calls}
    assert tables == {"evaluation_run", "evaluation_result", "evaluation_metric"}
    assert "evaluation_run_log" not in tables

    metric_names = {m.metric_name for m in repos.metrics}
    assert metric_names == set(MVP_METRIC_NAMES)

    phase_names = {p["phase"] for p in repos.phase_logs}
    assert PHASE_EVALUATION_COMPLETED in phase_names
    assert "dataset_resolved" in phase_names


def test_rerun_creates_new_evaluation_run() -> None:
    repos, _ = _repos()
    first = _run(repos, job_run_id="run-a")
    second = _run(repos, job_run_id="run-b")

    assert first.evaluation_run_id != second.evaluation_run_id
    assert len(repos.runs) == 2
    assert repos.run_insert_count == 2
    assert repos.result_insert_count == 4


def test_result_unique_rejects_duplicate_insert() -> None:
    repos, _ = _repos()
    _run(repos)
    run_id = repos.runs[0].evaluation_run_id
    dup = EvaluationResultRow(
        evaluation_result_id="dup-result",
        evaluation_run_id=run_id,
        evaluation_case_id=_CASE_1,
        evaluation_dataset_id=_DS,
    )
    try:
        repos.insert_result(dup)
        raise AssertionError("expected DuplicateInsertError")
    except DuplicateInsertError:
        pass
    assert repos.result_update_count == 0


def test_metric_unique_rejects_duplicate_name() -> None:
    repos, _ = _repos()
    result = _run(repos)
    assert result.metrics_inserted == 8
    result_id = repos.results[0].evaluation_result_id
    scores = calculate_mvp_metrics(
        predicted_item_ids=("a", "b"),
        expected_result_json={"golden_item_ids": ["a", "b"]},
    )
    try:
        repos.insert_metrics(evaluation_result_id=result_id, scores=scores)
        raise AssertionError("expected DuplicateInsertError")
    except DuplicateInsertError:
        pass
    assert repos.metric_update_count == 0


def test_inactive_dataset_fails_without_run() -> None:
    repos, _ = _repos(active=False)
    result = _run(repos)
    assert result.status == "failed"
    assert "GRS-CFG-001" in result.error_codes
    assert repos.run_insert_count == 0


def test_missing_expected_skips_metrics_but_keeps_result() -> None:
    repos, _ = _repos(
        cases=[
            EvaluationCaseRow(
                evaluation_case_id=_CASE_1,
                evaluation_dataset_id=_DS,
                case_label="case_001",
                expected_result_json=None,
                is_active=True,
            )
        ]
    )
    result = _run(repos)
    assert result.status == "succeeded"
    assert result.results_inserted == 1
    assert result.metrics_inserted == 0
    assert any(e["code"] == "GRS-EVAL-003" for e in repos.error_logs)


def test_mock_reco_failure_inserts_result_without_recommendation_id() -> None:
    repos, _ = _repos(
        cases=[
            EvaluationCaseRow(
                evaluation_case_id=_CASE_1,
                evaluation_dataset_id=_DS,
                case_label="case_001",
                expected_result_json={"golden_item_ids": ["a"]},
                is_active=True,
            )
        ]
    )
    reco = MockRecoEvaluationClient(fail_case_ids=frozenset({_CASE_1}))
    result = _run(repos, reco=reco)
    assert result.status == "partially_succeeded"
    assert result.results_inserted == 1
    assert repos.results[0].recommendation_result_id is None
    assert result.http_call_count == 0
    assert reco.call_count == 1


def test_metric_calculators_basic() -> None:
    relevant = frozenset({"a", "b", "c"})
    predicted = ("a", "x", "b", "y", "z")
    assert precision_at_k(predicted, relevant, k=5) == 2 / 5
    assert recall_at_k(predicted, relevant, k=5) == 2 / 3
    assert mrr_at_k(predicted, relevant, k=5) == 1.0
    assert 0.0 < ndcg_at_k(predicted, relevant, k=5) <= 1.0

    scores = calculate_mvp_metrics(
        predicted_item_ids=predicted,
        expected_result_json={"golden_item_ids": ["a", "b", "c"]},
    )
    assert tuple(s.metric_name for s in scores) == MVP_METRIC_NAMES


def test_scaffold_demo_cli_and_exit_codes() -> None:
    job = build_scaffold_demo_job()
    result = job.run(
        job_run_id="demo-run",
        evaluation_dataset_id="ds-scaffold-018",
        now=_NOW,
    )
    assert result.status == "succeeded"
    assert result.metrics_inserted == 8

    assert main(["--scaffold-demo", "--job-run-id", "cli-demo"]) == 0
    assert main(["--job-run-id", "real-off"]) == 3


def test_config_offline_evaluation_env_keys() -> None:
    settings = scaffold_batch_settings()
    assert settings.batch_offline_evaluation_dataset_id is None
    assert settings.batch_offline_evaluation_dry_run is False

    loaded = load_batch_settings(
        environ={
            "APP_ENV": "dev",
            "BATCH_OFFLINE_EVALUATION_DATASET_ID": "ds-env",
            "BATCH_OFFLINE_EVALUATION_DATASET_NAME": "name-env",
            "BATCH_OFFLINE_EVALUATION_DATASET_VERSION": "v9",
            "BATCH_OFFLINE_EVALUATION_MAX_CASES": "3",
            "BATCH_OFFLINE_EVALUATION_DRY_RUN": "true",
        }
    )
    assert loaded.batch_offline_evaluation_dataset_id == "ds-env"
    assert loaded.batch_offline_evaluation_dataset_name == "name-env"
    assert loaded.batch_offline_evaluation_dataset_version == "v9"
    assert loaded.batch_offline_evaluation_max_cases == 3
    assert loaded.batch_offline_evaluation_dry_run is True


def test_max_cases_limits_evaluation() -> None:
    repos, _ = _repos()
    result = _run(repos, max_cases=1)
    assert result.cases_evaluated == 1
    assert result.results_inserted == 1
    assert result.metrics_inserted == 4
