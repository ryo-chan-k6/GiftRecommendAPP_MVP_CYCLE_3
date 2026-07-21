"""Unit tests for BATCH-018 Offline Evaluation（仕様書 §16 unit 観点）.

fixture/mock のみ。実 DB / secret / 実 reco HTTP に依存しない。
"""

from __future__ import annotations

from datetime import UTC, datetime

from batch.application.offline_evaluation import (
    BATCH_ID,
    METRIC_K,
    MVP_METRIC_NAMES,
    OFFLINE_EVALUATION_PHASES,
    PHASE_EVALUATION_COMPLETED,
    DuplicateInsertError,
    EvaluationCaseRow,
    EvaluationDatasetRow,
    EvaluationMetricRow,
    EvaluationResultRow,
    OfflineEvaluationJob,
    OfflineEvaluationRepositories,
    calculate_mvp_metrics,
    extract_relevant_item_ids,
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

_FORBIDDEN_SECRET_TOKENS = (
    "sk-",
    "openai_api_key",
    "api_key",
    "bearer ",
    "password",
    "secret_token",
    "postgresql://",
    "DATABASE_URL",
    "supabase",
    "service_role",
)


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
    evaluation_dataset_id: str | None = _DS,
    dataset_name: str | None = None,
    dataset_version: str | None = None,
):
    job = OfflineEvaluationJob(
        repositories=repos,
        reco_client=reco or MockRecoEvaluationClient(),
        job_run_tracker=tracker,
    )
    return job.run(
        job_run_id=job_run_id,
        evaluation_dataset_id=evaluation_dataset_id,
        dataset_name=dataset_name,
        dataset_version=dataset_version,
        max_cases=max_cases,
        dry_run=dry_run,
        now=_NOW,
    )


# --- §16 No.1 IF-DB-BATCH-018 INSERT / phases ---------------------------------


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


def test_if_db_batch_018_write_payload_marks_insert_only() -> None:
    """IF-DB-BATCH-018 の書込が run/result/metric INSERT に閉じる."""

    repos, db = _repos()
    _run(repos)

    tables = {str(call["table"]) for call in db.write_calls}
    assert tables == {
        "evaluation_run",
        "evaluation_result",
        "evaluation_metric",
    }
    # result / metric は INSERT のみ（update_count 常時 0）
    assert repos.result_update_count == 0
    assert repos.metric_update_count == 0
    assert not hasattr(repos, "update_result")
    assert not hasattr(repos, "update_metric")

    # Run は INSERT + status UPDATE のみ（payload op で区別）
    run_ops = {
        str(row.get("op"))
        for call in db.write_calls
        if call["table"] == "evaluation_run"
        for row in call["rows"]  # type: ignore[union-attr]
    }
    assert "if_db_batch_018_insert" in run_ops
    assert "if_db_batch_018_status_update" in run_ops


# --- §16 No.2 IF-SHARED-004 mock 完走 ----------------------------------------


def test_if_shared_004_mock_completes_case_loop_without_http() -> None:
    repos, _ = _repos()
    reco = MockRecoEvaluationClient()
    result = _run(repos, reco=reco)

    assert result.status == "succeeded"
    assert reco.call_count == 2
    assert result.http_call_count == 0
    assert reco.last_request is not None
    assert reco.last_request.mode == "evaluation"
    assert result.results_inserted == 2
    assert result.metrics_inserted == 8


# --- §16 No.3 Run 毎回新規 INSERT --------------------------------------------


def test_rerun_creates_new_evaluation_run() -> None:
    repos, _ = _repos()
    first = _run(repos, job_run_id="run-a")
    second = _run(repos, job_run_id="run-b")

    assert first.evaluation_run_id != second.evaluation_run_id
    assert len(repos.runs) == 2
    assert repos.run_insert_count == 2
    assert repos.result_insert_count == 4
    run_ids = {r.evaluation_run_id for r in repos.runs}
    assert len(run_ids) == 2


# --- §16 No.4 / No.5 UNIQUE・UPDATE なし ------------------------------------


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
    assert repos.result_insert_count == 2  # 二重 INSERT は加算されない想定


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


def test_no_result_or_metric_update_path_on_rerun() -> None:
    """再実行は別 run を新規 INSERT し、既存 result/metric を UPDATE しない."""

    repos, _ = _repos()
    _run(repos, job_run_id="run-1")
    _run(repos, job_run_id="run-2")
    assert repos.result_update_count == 0
    assert repos.metric_update_count == 0
    assert repos.evaluation_run_log_write_count == 0


# --- §16 No.6 evaluation_run_log 非書込 --------------------------------------


def test_evaluation_run_log_never_written() -> None:
    repos, db = _repos()
    _run(repos)
    assert repos.evaluation_run_log_write_count == 0
    assert all(call["table"] != "evaluation_run_log" for call in db.write_calls)


# --- §16 No.7 初版メトリクス 4 種のみ ----------------------------------------


def test_mvp_metric_set_is_exactly_four_at_10() -> None:
    assert MVP_METRIC_NAMES == (
        "precision_at_10",
        "recall_at_10",
        "ndcg_at_10",
        "mrr_at_10",
    )
    assert METRIC_K == 10

    repos, _ = _repos(cases=[
        EvaluationCaseRow(
            evaluation_case_id=_CASE_1,
            evaluation_dataset_id=_DS,
            case_label="case_001",
            expected_result_json={"golden_item_ids": ["a", "b"]},
            is_active=True,
        )
    ])
    result = _run(repos)
    assert result.metrics_inserted == 4
    names = [m.metric_name for m in repos.metrics]
    assert names == list(MVP_METRIC_NAMES)


# --- §16 No.10 UT fixture（本番 seed 非含有） --------------------------------


def test_dataset_and_case_are_fixture_only_no_writes() -> None:
    repos, db = _repos()
    _run(repos)
    assert repos.dataset_write_count == 0
    assert repos.case_write_count == 0
    assert "evaluation_dataset" not in {c["table"] for c in db.write_calls}
    assert "evaluation_case" not in {c["table"] for c in db.write_calls}


# --- 部分成功 / concurrency GRS-BAT-* ----------------------------------------


def test_partial_success_grs_bat_002_on_reco_failure() -> None:
    repos, _ = _repos()
    reco = MockRecoEvaluationClient(fail_case_ids=frozenset({_CASE_2}))
    result = _run(repos, reco=reco)

    assert result.status == "partially_succeeded"
    assert "GRS-BAT-002" in result.error_codes
    assert result.results_inserted == 2
    # 失敗 case は recommendation_result_id なし、成功 case はあり
    by_case = {r.evaluation_case_id: r for r in repos.results}
    assert by_case[_CASE_1].recommendation_result_id is not None
    assert by_case[_CASE_2].recommendation_result_id is None
    assert result.http_call_count == 0
    assert reco.call_count == 2

    completed = [
        p for p in repos.phase_logs if p.get("phase") == PHASE_EVALUATION_COMPLETED
    ]
    assert completed
    assert completed[-1]["status"] == "partially_succeeded"


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
    assert "GRS-BAT-002" in result.error_codes


def test_already_running_grs_bat_003() -> None:
    tracker = ScaffoldJobRunTracker()
    tracker.start(batch_id=BATCH_ID, job_run_id="other")
    repos, db = _repos()
    result = _run(repos, tracker=tracker)

    assert "GRS-BAT-003" in result.error_codes
    assert result.status == "failed"
    assert repos.run_insert_count == 0
    assert result.results_inserted == 0
    assert db.write_calls == []


# --- 異常系 / dry_run / resolve ----------------------------------------------


def test_inactive_dataset_fails_without_run() -> None:
    repos, _ = _repos(active=False)
    result = _run(repos)
    assert result.status == "failed"
    assert "GRS-CFG-001" in result.error_codes
    assert repos.run_insert_count == 0


def test_missing_dataset_fails_grs_cfg_001() -> None:
    repos, db = _repos(include_dataset=False, cases=[])
    result = _run(repos, evaluation_dataset_id="missing-ds")
    assert result.status == "failed"
    assert "GRS-CFG-001" in result.error_codes
    assert db.write_calls == []


def test_no_active_cases_fails_grs_val_001() -> None:
    repos, db = _repos(cases=[])
    result = _run(repos)
    assert result.status == "failed"
    assert "GRS-VAL-001" in result.error_codes
    assert repos.run_insert_count == 0
    assert db.write_calls == []


def test_resolve_dataset_by_name_and_version() -> None:
    repos, _ = _repos()
    result = _run(
        repos,
        evaluation_dataset_id=None,
        dataset_name="offline_eval_ut",
        dataset_version="v1",
    )
    assert result.status == "succeeded"
    assert result.evaluation_dataset_id == _DS


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


def test_empty_golden_item_ids_skips_metrics() -> None:
    repos, _ = _repos(
        cases=[
            EvaluationCaseRow(
                evaluation_case_id=_CASE_1,
                evaluation_dataset_id=_DS,
                case_label="case_001",
                expected_result_json={"golden_item_ids": []},
                is_active=True,
            )
        ]
    )
    result = _run(repos)
    assert result.status == "succeeded"
    assert result.results_inserted == 1
    assert result.metrics_inserted == 0


def test_dry_run_evaluates_without_if_db_writes() -> None:
    repos, db = _repos()
    reco = MockRecoEvaluationClient()
    result = _run(repos, reco=reco, dry_run=True)

    assert result.status == "succeeded"
    assert result.dry_run is True
    assert result.cases_evaluated == 2
    assert result.results_inserted == 0
    assert result.metrics_inserted == 0
    assert repos.run_insert_count == 0
    assert repos.result_insert_count == 0
    assert repos.metric_insert_count == 0
    assert db.write_calls == []
    assert reco.call_count == 2
    assert result.http_call_count == 0


def test_max_cases_limits_evaluation() -> None:
    repos, _ = _repos()
    result = _run(repos, max_cases=1)
    assert result.cases_evaluated == 1
    assert result.results_inserted == 1
    assert result.metrics_inserted == 4


# --- メトリクス計算器 --------------------------------------------------------


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


def test_metric_calculators_edge_cases() -> None:
    relevant = frozenset({"a", "b"})
    assert precision_at_k((), relevant, k=10) == 0.0
    assert recall_at_k(("x", "y"), frozenset(), k=10) == 0.0
    assert mrr_at_k(("x", "y"), relevant, k=10) == 0.0
    assert ndcg_at_k(("a", "b"), relevant, k=10) == 1.0
    assert extract_relevant_item_ids(None) == frozenset()
    assert extract_relevant_item_ids({"golden_item_ids": "not-a-list"}) == frozenset()
    assert calculate_mvp_metrics(
        predicted_item_ids=("a",),
        expected_result_json=None,
    ) == ()
    assert calculate_mvp_metrics(
        predicted_item_ids=("a",),
        expected_result_json={"golden_item_ids": []},
    ) == ()


def test_metric_at_10_truncates_predictions() -> None:
    relevant = frozenset({f"i{i}" for i in range(15)})
    predicted = tuple(f"i{i}" for i in range(20))
    # k=10 なので上位 10 件のみヒット
    assert precision_at_k(predicted, relevant, k=METRIC_K) == 1.0
    scores = calculate_mvp_metrics(
        predicted_item_ids=predicted,
        expected_result_json={"golden_item_ids": list(relevant)},
    )
    assert scores[0].metric_name == "precision_at_10"
    assert scores[0].metric_value == 1.0
    assert scores[0].metric_detail_json is not None
    assert scores[0].metric_detail_json["k"] == 10


# --- CLI / config / secret ---------------------------------------------------


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


def test_fixture_and_printed_output_have_no_secret_like_values(capsys) -> None:
    """§16 No.11: fixture / ログ / CLI 出力に secret らしい文字列を含めない."""

    cases = [
        EvaluationCaseRow(
            evaluation_case_id=_CASE_1,
            evaluation_dataset_id=_DS,
            case_label="case_001",
            expected_result_json={"golden_item_ids": ["item-a", "item-b"]},
            input_condition_json={"relationship": "friend", "occasion": "birthday"},
            is_active=True,
        )
    ]
    blob = str(cases).lower()
    for token in _FORBIDDEN_SECRET_TOKENS:
        assert token not in blob

    repos, _ = _repos(cases=cases)
    _run(repos)
    for log in repos.error_logs + repos.phase_logs:
        text = str(log).lower()
        for token in _FORBIDDEN_SECRET_TOKENS:
            assert token not in text

    for row in repos.runs + repos.results + repos.metrics:
        text = str(row).lower()
        for token in _FORBIDDEN_SECRET_TOKENS:
            assert token not in text

    assert main(["--scaffold-demo", "--job-run-id", "sec-check"]) == 0
    printed = capsys.readouterr().out.lower()
    for token in _FORBIDDEN_SECRET_TOKENS:
        assert token not in printed


def test_repository_metric_row_shape_matches_mvp_names() -> None:
    repos, _ = _repos(
        cases=[
            EvaluationCaseRow(
                evaluation_case_id=_CASE_1,
                evaluation_dataset_id=_DS,
                case_label="case_001",
                expected_result_json={"golden_item_ids": ["z"]},
                is_active=True,
            )
        ]
    )
    _run(repos)
    assert all(isinstance(m, EvaluationMetricRow) for m in repos.metrics)
    assert {m.metric_name for m in repos.metrics} == set(MVP_METRIC_NAMES)
