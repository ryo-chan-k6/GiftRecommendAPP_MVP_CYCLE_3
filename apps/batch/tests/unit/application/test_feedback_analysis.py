"""Unit tests for BATCH-019 Feedback分析（仕様書 §16 unit 観点）.

fixture/mock のみ。実 DB / secret / migration に依存しない。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from batch.application.feedback_analysis import (
    BATCH_ID,
    DEFAULT_NEGATIVE_RATING_THRESHOLD,
    FEEDBACK_ANALYSIS_PHASES,
    NEGATIVE_FEEDBACK_TYPES,
    PHASE_ANALYSIS_COMPLETED,
    FeedbackAnalysisJob,
    FeedbackAnalysisRepositories,
    RecommendationFeedbackRow,
    aggregate_metrics,
    classify_feedbacks,
    is_negative_feedback,
)
from batch.application.feedback_analysis.__main__ import build_scaffold_demo_job, main
from batch.application.job_run import ScaffoldJobRunTracker
from batch.config import BATCH_ENV_KEYS, load_batch_settings, scaffold_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter

_NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=UTC)

_PKG_ROOT = Path(__file__).resolve().parents[3] / "src" / "batch" / "application" / "feedback_analysis"
# .../apps/batch/tests/unit/application -> parents[5] = repo root
_REPO_ROOT = Path(__file__).resolve().parents[5]

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


def _feedback(
    *,
    fid: str,
    feedback_type: str,
    target: str = "item",
    rating: int = 3,
    submitted_at: datetime | None = None,
) -> RecommendationFeedbackRow:
    return RecommendationFeedbackRow(
        recommendation_feedback_id=fid,
        feedback_type=feedback_type,
        feedback_target_type=target,
        feedback_rating=rating,
        submitted_at=submitted_at or _NOW,
        recommendation_result_id="rr-1",
        recommendation_result_item_id="rri-1" if target == "item" else None,
        recommendation_reason_id="reason-1" if target == "reason" else None,
    )


def _repos(
    feedbacks: list[RecommendationFeedbackRow] | None = None,
) -> tuple[FeedbackAnalysisRepositories, ScaffoldDbWriter]:
    db = ScaffoldDbWriter()
    default = [
        _feedback(fid="fb-1", feedback_type="item_bad", rating=2),
        _feedback(fid="fb-2", feedback_type="item_good", rating=5),
        _feedback(
            fid="fb-3",
            feedback_type="reason_bad",
            target="reason",
            rating=1,
        ),
        _feedback(
            fid="fb-4",
            feedback_type="result_good",
            target="result",
            rating=4,
        ),
    ]
    repos = FeedbackAnalysisRepositories(
        db_writer=db,
        seed_feedbacks=feedbacks if feedbacks is not None else default,
    )
    return repos, db


def _run(
    repos: FeedbackAnalysisRepositories,
    *,
    job_run_id: str = "run-019-1",
    tracker: ScaffoldJobRunTracker | None = None,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    aggregation_scope: str | None = "weekly",
    feedback_types: str | None = None,
    dry_run: bool = False,
    max_feedback_rows: int | None = None,
    negative_rating_threshold: int = DEFAULT_NEGATIVE_RATING_THRESHOLD,
):
    job = FeedbackAnalysisJob(
        repositories=repos,
        job_run_tracker=tracker,
    )
    return job.run(
        job_run_id=job_run_id,
        period_start=period_start,
        period_end=period_end,
        aggregation_scope=aggregation_scope,
        feedback_types=feedback_types,
        dry_run=dry_run,
        max_feedback_rows=max_feedback_rows,
        negative_rating_threshold=negative_rating_threshold,
        now=_NOW,
    )


# --- §16 No.1 IF-DB-BATCH-019 stub / phases -----------------------------------


def test_happy_path_stub_persists_and_tracks_phases() -> None:
    repos, db = _repos()
    result = _run(repos)

    assert result.batch_id == BATCH_ID
    assert result.status == "succeeded"
    assert result.feedback_resolved_count == 4
    assert result.negative_count == 2
    assert result.results_stubbed == 7  # 3 summary + 4 feedback-unit
    assert "open_run" in result.completed_phases
    assert "finalize" in result.completed_phases
    for phase in FEEDBACK_ANALYSIS_PHASES:
        assert phase in result.completed_phases

    assert repos.stub_persist_count == 7
    assert repos.feedback_write_count == 0
    assert repos.feedback_update_count == 0
    assert repos.real_db_insert_count == 0
    assert repos.feedback_metric_table_write_count == 0
    assert result.feedback_write_count == 0
    assert result.real_db_insert_count == 0

    tables = {call["table"] for call in db.write_calls}
    assert tables == {"feedback_analysis_result_stub"}
    assert "recommendation_feedback" not in tables
    assert "feedback_metric" not in tables

    ops = {
        str(row.get("op"))
        for call in db.write_calls
        for row in call["rows"]  # type: ignore[union-attr]
    }
    assert ops == {"if_db_batch_019_stub"}

    phase_names = {p["phase"] for p in repos.phase_logs}
    assert PHASE_ANALYSIS_COMPLETED in phase_names
    assert "feedback_resolved" in phase_names
    assert "classified" in phase_names
    assert "aggregated" in phase_names
    assert "analysis_persisted" in phase_names
    assert all(p["owner_type"] == "batch_run" for p in repos.phase_logs)


def test_if_db_batch_019_is_in_memory_stub_only() -> None:
    """IF-DB-BATCH-019: ScaffoldDbWriter 記録のみ。実 INSERT カウンタは常に 0."""

    repos, db = _repos()
    result = _run(repos)

    assert result.real_db_insert_count == 0
    assert repos.real_db_insert_count == 0
    assert isinstance(db, ScaffoldDbWriter)
    for call in db.write_calls:
        assert call["table"] == "feedback_analysis_result_stub"
        for row in call["rows"]:  # type: ignore[union-attr]
            assert row["op"] == "if_db_batch_019_stub"
            assert row["feedback_metric_table"] is None


def test_metrics_embedded_in_analysis_result_json() -> None:
    """feedback_metric は独立テーブルではなく JSON 内包（§18.1 No.17）."""

    repos, _db = _repos()
    _run(repos)

    period_rows = [
        r for r in repos.analysis_results if r.analysis_type == "period_aggregate"
    ]
    assert len(period_rows) == 1
    payload = period_rows[0].analysis_result_json
    assert "metrics" in payload
    metrics = payload["metrics"]
    assert isinstance(metrics, dict)
    assert metrics["total_count"] == 4
    assert metrics["negative_count"] == 2
    assert "by_feedback_type" in metrics
    assert "item_bad" in metrics["by_feedback_type"]

    type_rows = [r for r in repos.analysis_results if r.analysis_type == "type_breakdown"]
    assert any("metrics" in r.analysis_result_json for r in type_rows)

    neg_rows = [
        r for r in repos.analysis_results if r.analysis_type == "negative_trend"
    ]
    assert len(neg_rows) == 1
    assert "metrics" in neg_rows[0].analysis_result_json
    assert repos.feedback_metric_table_write_count == 0


# --- §16 No.2 recommendation_feedback UPDATE 禁止 -----------------------------


def test_recommendation_feedback_is_read_only() -> None:
    repos, db = _repos()
    before = list(repos.feedbacks)
    _run(repos)

    assert repos.feedback_write_count == 0
    assert repos.feedback_update_count == 0
    assert not hasattr(repos, "update_feedback")
    assert not hasattr(repos, "insert_feedback")
    assert "recommendation_feedback" not in {
        str(call["table"]) for call in db.write_calls
    }
    # fixture は SELECT 相当で不変
    assert repos.feedbacks == before


def test_load_feedbacks_select_only_does_not_mutate_seed() -> None:
    repos, _db = _repos()
    seed_ids = [r.recommendation_feedback_id for r in repos.feedbacks]
    loaded = repos.load_feedbacks()
    assert len(loaded) == 4
    assert [r.recommendation_feedback_id for r in repos.feedbacks] == seed_ids
    assert repos.feedback_write_count == 0
    assert repos.feedback_update_count == 0


# --- §16 No.3 migration / 出力物理 DDL 非含有 ---------------------------------


def test_package_has_no_migration_or_physical_ddl() -> None:
    """実装パッケージに CREATE TABLE / migration 記述がない（差分確認の unit 代替）."""

    assert _PKG_ROOT.is_dir()
    forbidden_snippets = (
        "CREATE TABLE",
        "create table",
        "supabase/migrations",
        "ALTER TABLE feedback_analysis_result",
        "ALTER TABLE feedback_metric",
    )
    for path in _PKG_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for snippet in forbidden_snippets:
            assert snippet not in text, f"{path.name} contains {snippet!r}"

    migrations_dir = _REPO_ROOT / "supabase" / "migrations"
    if migrations_dir.is_dir():
        for path in migrations_dir.glob("*.sql"):
            text = path.read_text(encoding="utf-8").lower()
            assert "feedback_analysis_result" not in text
            assert "create table feedback_metric" not in text


# --- §16 No.4 / No.5 / No.6 モジュール境界 ------------------------------------


def test_mod_batch_042_exports_analyzer_internals() -> None:
    """MOD-BATCH-042 が正。Aggregator / Classifier はパッケージ公開 API."""

    import batch.application.feedback_analysis as pkg

    assert hasattr(pkg, "FeedbackAnalysisJob")
    assert hasattr(pkg, "classify_feedbacks")
    assert hasattr(pkg, "aggregate_metrics")
    assert hasattr(pkg, "is_negative_feedback")
    assert BATCH_ID == "BATCH-019"


def test_no_mod_batch_043_044_modules() -> None:
    import batch.application.feedback_analysis as pkg

    assert not hasattr(pkg, "FailureAnalyzer")
    assert not hasattr(pkg, "ImprovementBacklogGenerator")

    text = "\n".join(p.read_text(encoding="utf-8") for p in _PKG_ROOT.glob("*.py"))
    assert "FailureAnalyzer" not in text
    assert "ImprovementBacklogGenerator" not in text
    # 言及は out of scope 注記のみ可。実装 import は禁止
    assert "from batch.application.failure" not in text
    assert "from batch.application.improvement" not in text


def test_no_mod_batch_019_raw_reader_confusion() -> None:
    """MOD-BATCH-019（Raw Product Reader）と Batch ID BATCH-019 を混同しない."""

    import batch.application.feedback_analysis as pkg

    assert not hasattr(pkg, "RawProductReader")
    assert not hasattr(pkg, "read_raw_product")
    text = "\n".join(p.read_text(encoding="utf-8") for p in _PKG_ROOT.glob("*.py"))
    assert "RawProductReader" not in text
    assert "batch.application.raw" not in text


# --- §16 No.12 feedback_analysis_status 読み替え ------------------------------


def test_feedback_analysis_status_via_phase_log_and_tracker() -> None:
    """専用 status 列なし。phase_log + batch_run_log（tracker）で読み替え."""

    tracker = ScaffoldJobRunTracker()
    repos, _db = _repos()
    result = _run(repos, tracker=tracker)

    assert result.status == "succeeded"
    assert any(p["phase"] == PHASE_ANALYSIS_COMPLETED for p in repos.phase_logs)
    assert all(p["owner_type"] == "batch_run" for p in repos.phase_logs)
    assert not hasattr(repos, "feedback_analysis_status")
    completed = [
        r
        for r in tracker.records
        if getattr(r, "batch_id", None) == BATCH_ID
        and getattr(r, "status", None) == "succeeded"
    ]
    assert len(completed) >= 1


# --- Classifier / Aggregator -------------------------------------------------


def test_negative_classifier_and_aggregator() -> None:
    rows = (
        _feedback(fid="a", feedback_type="item_ng_violation", rating=5),
        _feedback(fid="b", feedback_type="item_good", rating=1),
        _feedback(fid="c", feedback_type="result_good", target="result", rating=4),
    )
    assert is_negative_feedback(rows[0]) is True
    assert is_negative_feedback(rows[1]) is True  # low rating
    assert is_negative_feedback(rows[2]) is False
    assert "item_ng_violation" in NEGATIVE_FEEDBACK_TYPES

    negatives, others = classify_feedbacks(rows)
    assert len(negatives) == 2
    assert len(others) == 1

    metrics = aggregate_metrics(
        rows,
        negatives=negatives,
        aggregation_scope="manual",
        rating_threshold=DEFAULT_NEGATIVE_RATING_THRESHOLD,
    )
    assert metrics["total_count"] == 3
    assert metrics["negative_count"] == 2
    assert metrics["negative_ratio"] == 2 / 3


def test_positive_and_negative_aggregation_counts() -> None:
    """Negative / Positive（Non-negative）集計がメトリクスに反映される."""

    rows = [
        _feedback(fid="n1", feedback_type="item_bad", rating=1),
        _feedback(fid="n2", feedback_type="result_bad", target="result", rating=5),
        _feedback(fid="p1", feedback_type="item_good", rating=5),
        _feedback(fid="p2", feedback_type="result_good", target="result", rating=4),
        _feedback(fid="p3", feedback_type="reason_good", target="reason", rating=3),
    ]
    repos, _db = _repos(rows)
    result = _run(repos)

    assert result.status == "succeeded"
    assert result.feedback_resolved_count == 5
    assert result.negative_count == 2

    period = next(
        r for r in repos.analysis_results if r.analysis_type == "period_aggregate"
    )
    metrics = period.analysis_result_json["metrics"]
    assert metrics["total_count"] == 5
    assert metrics["negative_count"] == 2
    assert metrics["negative_ratio"] == 2 / 5
    assert metrics["by_feedback_type"]["item_good"] == 1
    assert metrics["by_feedback_type"]["item_bad"] == 1

    negatives, positives = classify_feedbacks(tuple(rows))
    assert len(negatives) == 2
    assert len(positives) == 3


def test_period_filter_and_empty_success() -> None:
    repos, _db = _repos(
        [
            _feedback(
                fid="old",
                feedback_type="item_bad",
                submitted_at=_NOW - timedelta(days=30),
            )
        ]
    )
    result = _run(
        repos,
        period_start=_NOW - timedelta(days=1),
        period_end=_NOW,
    )
    assert result.status == "succeeded"
    assert result.feedback_resolved_count == 0
    # 空でも集計サマリ 3 stub
    assert result.results_stubbed == 3


def test_empty_feedback_fixture_succeeds_with_summary_stubs() -> None:
    repos, db = _repos([])
    result = _run(repos)
    assert result.status == "succeeded"
    assert result.feedback_resolved_count == 0
    assert result.negative_count == 0
    assert result.results_stubbed == 3
    assert repos.stub_persist_count == 3
    assert {call["table"] for call in db.write_calls} == {
        "feedback_analysis_result_stub"
    }


def test_feedback_types_filter() -> None:
    repos, _db = _repos()
    result = _run(repos, feedback_types="item_bad,item_good")
    assert result.status == "succeeded"
    assert result.feedback_resolved_count == 2
    assert result.results_stubbed == 5  # 3 summary + 2 unit


def test_max_feedback_rows_limits_resolve() -> None:
    repos, _db = _repos()
    result = _run(repos, max_feedback_rows=1)
    assert result.status == "succeeded"
    assert result.feedback_resolved_count == 1
    assert result.results_stubbed == 4  # 3 summary + 1 unit


def test_invalid_period_fails_validation() -> None:
    repos, _db = _repos()
    result = _run(
        repos,
        period_start=_NOW,
        period_end=_NOW - timedelta(days=1),
    )
    assert result.status == "failed"
    assert "GRS-VAL-001" in result.error_codes
    assert repos.stub_persist_count == 0


def test_dry_run_skips_stub_persist() -> None:
    repos, db = _repos()
    result = _run(repos, dry_run=True)
    assert result.status == "succeeded"
    assert result.results_stubbed == 0
    assert repos.stub_persist_count == 0
    assert db.write_calls == []


def test_idempotent_scaffold_creates_new_stubs_each_run() -> None:
    """scaffold 冪等: 実行都度新規 stub（§18.1 No.20）."""

    repos, _db = _repos()
    first = _run(repos, job_run_id="run-a")
    second = _run(repos, job_run_id="run-b")
    assert first.status == "succeeded"
    assert second.status == "succeeded"
    assert first.results_stubbed == second.results_stubbed
    assert len(repos.analysis_results) == first.results_stubbed + second.results_stubbed
    ids = [r.feedback_analysis_result_id for r in repos.analysis_results]
    assert len(ids) == len(set(ids))


def test_already_running_returns_grs_bat_003() -> None:
    """concurrency: 既存 running がある場合 GRS-BAT-003."""

    tracker = ScaffoldJobRunTracker()
    tracker.start(batch_id=BATCH_ID, job_run_id="running-1")
    repos, _db = _repos()
    result = _run(repos, tracker=tracker, job_run_id="running-2")
    assert result.status == "failed"
    assert "GRS-BAT-003" in result.error_codes
    assert repos.stub_persist_count == 0


def test_partial_success_grs_bat_002_not_implemented_in_scaffold() -> None:
    """部分成功 GRS-BAT-002 / partially_succeeded 経路は scaffold 未実装（実装にあれば検証）.

    事実: finalize は succeeded / failed のみ。GRS-BAT-002 は付与されない。
    """

    repos, _db = _repos()
    result = _run(repos)
    assert result.status == "succeeded"
    assert "GRS-BAT-002" not in result.error_codes
    assert result.status != "partially_succeeded"

    # ソース上も GRS-BAT-002 を発火しない
    job_src = (_PKG_ROOT / "job.py").read_text(encoding="utf-8")
    assert "GRS-BAT-002" not in job_src


def test_negative_rating_threshold_override() -> None:
    rows = [_feedback(fid="x", feedback_type="item_good", rating=3)]
    repos, _db = _repos(rows)
    # 閾値 3 → rating<=3 は Negative
    result = _run(repos, negative_rating_threshold=3)
    assert result.negative_count == 1
    # 閾値 2 → rating 3 は Positive
    repos2, _ = _repos(rows)
    result2 = _run(repos2, negative_rating_threshold=2)
    assert result2.negative_count == 0


# --- CLI / config / secret ----------------------------------------------------


def test_scaffold_demo_cli_succeeds() -> None:
    code = main(["--scaffold-demo", "--job-run-id", "cli-019"])
    assert code == 0


def test_non_scaffold_demo_exits_3() -> None:
    code = main(["--job-run-id", "real-off"])
    assert code == 3


def test_build_scaffold_demo_job_runs() -> None:
    job = build_scaffold_demo_job()
    result = job.run(job_run_id="demo-1", now=_NOW)
    assert result.status == "succeeded"
    assert result.feedback_resolved_count >= 1


def test_config_batch_feedback_analysis_env_keys() -> None:
    assert "BATCH_FEEDBACK_ANALYSIS_PERIOD_START" in BATCH_ENV_KEYS
    assert "BATCH_FEEDBACK_ANALYSIS_MAX_FEEDBACK_ROWS" in BATCH_ENV_KEYS
    assert "BATCH_FEEDBACK_ANALYSIS_DRY_RUN" in BATCH_ENV_KEYS
    assert "BATCH_FEEDBACK_ANALYSIS_NEGATIVE_RATING_THRESHOLD" in BATCH_ENV_KEYS

    settings = scaffold_batch_settings()
    assert settings.batch_feedback_analysis_dry_run is False
    assert settings.batch_feedback_analysis_negative_rating_threshold == 2

    loaded = load_batch_settings(
        environ={
            "APP_ENV": "dev",
            "OBJECT_STORAGE_BUCKET": "raw-dev",
            "BATCH_FEEDBACK_ANALYSIS_AGGREGATION_SCOPE": "weekly",
            "BATCH_FEEDBACK_ANALYSIS_MAX_FEEDBACK_ROWS": "100",
            "BATCH_FEEDBACK_ANALYSIS_DRY_RUN": "true",
            "BATCH_FEEDBACK_ANALYSIS_NEGATIVE_RATING_THRESHOLD": "2",
        }
    )
    assert loaded.batch_feedback_analysis_aggregation_scope == "weekly"
    assert loaded.batch_feedback_analysis_max_feedback_rows == 100
    assert loaded.batch_feedback_analysis_dry_run is True
    assert loaded.batch_feedback_analysis_negative_rating_threshold == 2


def test_stub_payload_has_no_secret_tokens() -> None:
    repos, db = _repos()
    _run(repos)
    blob = str(db.write_calls).lower()
    for token in _FORBIDDEN_SECRET_TOKENS:
        assert token.lower() not in blob


def test_fixture_phase_logs_and_cli_have_no_secret_tokens(capsys) -> None:
    repos, _db = _repos()
    _run(repos)
    for log in repos.error_logs + repos.phase_logs:
        text = str(log).lower()
        for token in _FORBIDDEN_SECRET_TOKENS:
            assert token.lower() not in text

    assert main(["--scaffold-demo", "--job-run-id", "sec-check"]) == 0
    printed = capsys.readouterr().out.lower()
    for token in _FORBIDDEN_SECRET_TOKENS:
        assert token.lower() not in printed


def test_independent_workflow_file_exists_without_parent_cron() -> None:
    """§16 No.7 相当: 独立子 workflow が存在し、cron schedule を持たない."""

    wf = _REPO_ROOT / ".github" / "workflows" / "batch-feedback-analysis.yml"
    assert wf.is_file()
    text = wf.read_text(encoding="utf-8")
    assert "schedule:" not in text
    assert "workflow_dispatch" in text
    assert "BATCH-019" in text or "feedback-analysis" in text
