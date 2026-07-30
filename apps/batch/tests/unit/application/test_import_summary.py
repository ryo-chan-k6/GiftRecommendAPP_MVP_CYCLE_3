"""Unit tests for BATCH-017 Import Summary 作成（仕様書 §16 最小 / scaffold-first）.

fixture/mock のみ。実 DB / secret に依存しない。
"""

from __future__ import annotations

from datetime import UTC, datetime

from batch.application.import_summary import (
    BATCH_ID,
    IMPORT_SUMMARY_PHASES,
    PHASE_SUMMARY_CREATED,
    ApiCallLogRow,
    BatchRunLogRow,
    FeatureEmbeddingProgress,
    ImportSummaryJob,
    ImportSummaryRepositories,
    ProductDiffRow,
    SkipFailCounts,
    StagingItemRow,
    aggregate_diff_counts,
    aggregate_fetched_count,
    resolve_source_api,
)
from batch.application.import_summary.__main__ import build_scaffold_demo_job, main
from batch.application.job_run import ScaffoldJobRunTracker
from batch.config import load_batch_settings, scaffold_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter

_NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=UTC)
_RUN = "run-017-1"


def _repos(
    *,
    batch_run_id: str = _RUN,
    source_api: str = "item_search",
    api_calls: list[ApiCallLogRow] | None = None,
    diffs: list[ProductDiffRow] | None = None,
    staging: list[StagingItemRow] | None = None,
    skip_fail: SkipFailCounts | None = None,
    progress: FeatureEmbeddingProgress | None = None,
    include_run: bool = True,
) -> tuple[ImportSummaryRepositories, ScaffoldDbWriter]:
    db = ScaffoldDbWriter()
    typed_api = source_api  # type: ignore[assignment]
    repos = ImportSummaryRepositories(
        db_writer=db,
        seed_batch_runs=(
            [BatchRunLogRow(batch_run_id=batch_run_id, status="succeeded")]
            if include_run
            else []
        ),
        seed_api_calls=api_calls
        if api_calls is not None
        else [
            ApiCallLogRow(
                batch_run_id=batch_run_id, source_api=typed_api, item_count=3
            ),
            ApiCallLogRow(
                batch_run_id=batch_run_id, source_api=typed_api, item_count=2
            ),
        ],
        seed_diffs=diffs
        if diffs is not None
        else [
            ProductDiffRow(
                batch_run_id=batch_run_id, source_api="item_search", diff_status="new"
            ),
            ProductDiffRow(
                batch_run_id=batch_run_id,
                source_api="item_search",
                diff_status="updated",
            ),
            ProductDiffRow(
                batch_run_id=batch_run_id,
                source_api="item_search",
                diff_status="unchanged",
            ),
            ProductDiffRow(
                batch_run_id=batch_run_id,
                source_api="item_search",
                diff_status="unavailable",
            ),
        ],
        seed_staging_items=staging if staging is not None else [],
        seed_skip_fail=skip_fail or SkipFailCounts(skipped_count=1, failed_count=0),
        seed_feature_embedding=progress
        or FeatureEmbeddingProgress(
            feature_completed=False,
            feature_generated_count=9,
            embedding_completed=False,
            embedding_generated_count=8,
        ),
        seed_default_source_api=typed_api,
    )
    return repos, db


def _run(
    repos: ImportSummaryRepositories,
    *,
    job_run_id: str = _RUN,
    batch_run_id: str | None = None,
    source_api: str | None = "item_search",
    tracker: ScaffoldJobRunTracker | None = None,
):
    job = ImportSummaryJob(repositories=repos, job_run_tracker=tracker)
    return job.run(
        job_run_id=job_run_id,
        source_api=source_api,
        batch_run_id=job_run_id if batch_run_id is None else batch_run_id,
        now=_NOW,
    )


def test_happy_path_inserts_item_import_summary_and_summary_created_phase() -> None:
    repos, db = _repos()
    result = _run(repos)

    assert result.status == "succeeded"
    assert result.insert_applied is True
    assert result.conflict_skipped is False
    assert len(repos.summary_rows) == 1
    row = repos.summary_rows[0]
    assert row.batch_run_id == _RUN
    assert row.source_api == "item_search"
    assert row.fetched_count == 5
    assert row.new_count == 1
    assert row.updated_count == 1
    assert row.unchanged_count == 1
    assert row.unavailable_count == 1
    assert row.skipped_count == 1
    assert row.failed_count == 0
    assert row.feature_generated_count == 0
    assert row.embedding_generated_count == 0

    assert db.write_calls == []
    assert len(db.upsert_calls) == 1
    call = db.upsert_calls[0]
    assert call["table"] == "item_import_summary"
    assert call["conflict_columns"] == ("batch_run_id", "source_api")
    assert call["update_columns"] == ()
    payload = call["rows"][0]
    assert "op" not in payload
    assert "conflict_skipped" not in payload
    assert payload["summarized_at"] == _NOW
    assert isinstance(payload["summarized_at"], datetime)
    assert repos.phase_logs == [{"phase": PHASE_SUMMARY_CREATED, "status": "succeeded"}]

    idx = [result.completed_phases.index(p) for p in IMPORT_SUMMARY_PHASES]
    assert idx == sorted(idx)


def test_on_conflict_do_nothing_second_insert() -> None:
    repos, db = _repos()
    first = _run(repos)
    second = _run(repos)

    assert first.insert_applied is True
    assert second.insert_applied is False
    assert second.conflict_skipped is True
    assert len(repos.summary_rows) == 1
    assert repos.insert_attempt_count == 2
    assert repos.conflict_skip_count == 1
    assert repos.summary_update_count == 0
    assert len(db.upsert_calls) == 2
    assert all(c["update_columns"] == () for c in db.upsert_calls)
    for call in db.upsert_calls:
        for row in call["rows"]:
            assert "op" not in row
            assert "conflict_skipped" not in row


def test_no_update_path_on_repositories() -> None:
    repos, _ = _repos()
    assert not hasattr(repos, "update_summary")
    assert repos.summary_update_count == 0
    _run(repos)
    assert repos.summary_update_count == 0


def test_adjacent_if_and_business_tables_not_written() -> None:
    repos, db = _repos()
    result = _run(repos)

    assert result.feature_metric_write_count == 0
    assert result.meaning_metric_write_count == 0
    assert result.normalization_metric_write_count == 0
    assert result.product_diff_write_count == 0
    assert result.staging_item_write_count == 0
    assert result.item_write_count == 0

    forbidden = {
        "feature_distribution_metric",
        "meaning_distribution_metric",
        "normalization_distribution_metric",
        "product_diff_result",
        "staging_item",
        "item",
        "item_feature",
        "item_embedding",
    }
    written = {c["table"] for c in db.write_calls} | {c["table"] for c in db.upsert_calls}
    assert written.isdisjoint(forbidden)
    assert {c["table"] for c in db.upsert_calls} == {"item_import_summary"}

    for call in db.upsert_calls:
        assert call["update_columns"] == ()
        for row in call["rows"]:
            assert "op" not in row
            assert "conflict_skipped" not in row


def test_item_ranking_diff_counts_are_zero_fixed() -> None:
    repos, _ = _repos(
        source_api="item_ranking",
        api_calls=[
            ApiCallLogRow(
                batch_run_id=_RUN, source_api="item_ranking", item_count=10
            )
        ],
        diffs=[
            ProductDiffRow(
                batch_run_id=_RUN, source_api="item_ranking", diff_status="new"
            )
        ],
    )
    result = _run(repos, source_api="item_ranking")
    assert result.status == "succeeded"
    row = repos.summary_rows[0]
    assert row.fetched_count == 10
    assert row.new_count == 0
    assert row.updated_count == 0
    assert row.unchanged_count == 0
    assert row.unavailable_count == 0


def test_genre_search_diff_counts_are_zero_fixed() -> None:
    new_c, upd_c, unc_c, una_c = aggregate_diff_counts(
        diffs=[
            ProductDiffRow(
                batch_run_id=_RUN, source_api="genre_search", diff_status="updated"
            )
        ],
        batch_run_id=_RUN,
        source_api="genre_search",
    )
    assert (new_c, upd_c, unc_c, una_c) == (0, 0, 0, 0)


def test_fetched_count_uses_api_call_log_sum() -> None:
    fetched = aggregate_fetched_count(
        api_calls=[
            ApiCallLogRow(batch_run_id=_RUN, source_api="item_search", item_count=4),
            ApiCallLogRow(batch_run_id=_RUN, source_api="item_search", item_count=6),
        ],
        staging_items=[
            StagingItemRow(batch_run_id=_RUN, source_api="item_search"),
            StagingItemRow(batch_run_id=_RUN, source_api="item_search"),
        ],
        batch_run_id=_RUN,
        source_api="item_search",
    )
    assert fetched == 10


def test_fetched_count_falls_back_to_staging_when_item_count_all_zero() -> None:
    fetched = aggregate_fetched_count(
        api_calls=[
            ApiCallLogRow(batch_run_id=_RUN, source_api="item_search", item_count=0),
            ApiCallLogRow(batch_run_id=_RUN, source_api="item_search", item_count=0),
        ],
        staging_items=[
            StagingItemRow(batch_run_id=_RUN, source_api="item_search"),
            StagingItemRow(batch_run_id=_RUN, source_api="item_search"),
            StagingItemRow(batch_run_id=_RUN, source_api="item_search"),
        ],
        batch_run_id=_RUN,
        source_api="item_search",
    )
    assert fetched == 3


def test_feature_embedding_zero_when_not_completed() -> None:
    repos, _ = _repos(
        progress=FeatureEmbeddingProgress(
            feature_completed=False,
            feature_generated_count=5,
            embedding_completed=False,
            embedding_generated_count=4,
        )
    )
    result = _run(repos)
    assert result.summary_row is not None
    assert result.summary_row.feature_generated_count == 0
    assert result.summary_row.embedding_generated_count == 0


def test_feature_embedding_nonzero_when_completed() -> None:
    repos, _ = _repos(
        progress=FeatureEmbeddingProgress(
            feature_completed=True,
            feature_generated_count=5,
            embedding_completed=True,
            embedding_generated_count=4,
        )
    )
    result = _run(repos)
    assert result.summary_row is not None
    assert result.summary_row.feature_generated_count == 5
    assert result.summary_row.embedding_generated_count == 4


def test_invalid_source_api_fails() -> None:
    repos, db = _repos()
    result = _run(repos, source_api="not_a_source")
    assert result.status == "failed"
    assert "GRS-CFG-001" in result.error_codes
    assert repos.phase_logs == []
    assert db.write_calls == []
    assert db.upsert_calls == []


def test_missing_batch_run_fails() -> None:
    repos, db = _repos(include_run=False)
    result = _run(repos)
    assert result.status == "failed"
    assert "GRS-VAL-001" in result.error_codes
    assert repos.phase_logs == []
    assert db.write_calls == []
    assert db.upsert_calls == []


def test_ensures_pipeline_batch_run_when_missing_and_ids_differ(capsys) -> None:
    """#1726: job_run_id ≠ batch_run_id かつ pipeline 未作成なら ensure して継続."""

    pipeline = "pipeline-meaning-1"
    leaf = "leaf-017-1"
    repos, _ = _repos(batch_run_id=pipeline, include_run=False)
    tracker = ScaffoldJobRunTracker()
    result = _run(repos, job_run_id=leaf, batch_run_id=pipeline, tracker=tracker)

    assert result.status == "succeeded"
    assert result.insert_applied is True
    assert any(
        r.job_run_id == pipeline and r.batch_id == "item_meaning_pipeline"
        for r in tracker.records
    )
    assert "pipeline batch_run_log ensure" in capsys.readouterr().err


def test_already_running_grs_bat_003() -> None:
    tracker = ScaffoldJobRunTracker()
    tracker.start(batch_id=BATCH_ID, job_run_id="other")
    repos, db = _repos()
    result = _run(repos, tracker=tracker)
    assert "GRS-BAT-003" in result.error_codes
    assert result.status == "failed"
    assert db.write_calls == []
    assert db.upsert_calls == []


def test_cli_scaffold_demo_returns_zero(capsys) -> None:
    assert main(["--scaffold-demo", "--job-run-id", "cli"]) == 0
    out = capsys.readouterr().out
    assert "BATCH-017 scaffold demo" in out
    assert "status=succeeded" in out


def test_cli_without_scaffold_requires_database_url(monkeypatch) -> None:
    from dataclasses import replace

    from batch.application.import_summary import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings as scaffold_settings

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(scaffold_settings(), database_url=None),
    )
    assert cli.main(["--job-run-id", "cli"]) == 2


def test_require_and_loads_via_db_reader() -> None:
    from batch.infrastructure.db import ScaffoldDbReader

    reader = ScaffoldDbReader()
    reader.seed(
        "batch_run_log",
        (
            {
                "batch_run_id": _RUN,
                "run_status": "succeeded",
            },
        ),
    )
    reader.seed(
        "api_call_log",
        (
            {
                "api_call_log_id": "acl_1",
                "batch_run_id": _RUN,
                "source_api": "item_search",
                "item_count": 4,
            },
            {
                "api_call_log_id": "acl_other",
                "batch_run_id": "other-run",
                "source_api": "item_search",
                "item_count": 99,
            },
        ),
    )
    reader.seed(
        "product_diff_result",
        (
            {
                "product_diff_result_id": "pdr_1",
                "batch_run_id": _RUN,
                "staging_item_id": "si_1",
                "diff_status": "new",
            },
            {
                "product_diff_result_id": "pdr_2",
                "batch_run_id": _RUN,
                "staging_item_id": "si_2",
                "diff_status": "updated",
            },
        ),
    )
    reader.seed(
        "raw_product_metadata",
        (
            {
                "raw_metadata_id": "raw_1",
                "api_call_log_id": "acl_1",
                "source_api": "item_search",
            },
        ),
    )
    reader.seed(
        "staging_item",
        (
            {
                "staging_item_id": "si_1",
                "raw_metadata_id": "raw_1",
            },
            {
                "staging_item_id": "si_orphan",
                "raw_metadata_id": "raw_orphan",
            },
        ),
    )
    repos = ImportSummaryRepositories(
        db_writer=ScaffoldDbWriter(),
        db_reader=reader,
        seed_default_source_api="item_search",
    )
    run = repos.require_batch_run(_RUN)
    assert run.status == "succeeded"
    api_calls = repos.load_api_calls(batch_run_id=_RUN)
    assert len(api_calls) == 1
    assert api_calls[0].item_count == 4
    diffs = repos.load_diffs(batch_run_id=_RUN)
    assert len(diffs) == 2
    assert {d.diff_status for d in diffs} == {"new", "updated"}
    assert all(d.source_api == "item_search" for d in diffs)
    staging = repos.load_staging_items(batch_run_id=_RUN)
    assert len(staging) == 1
    assert staging[0].source_api == "item_search"
    assert any(c["table"] == "batch_run_log" for c in reader.fetch_calls)
    assert any(c["table"] == "api_call_log" for c in reader.fetch_calls)
    assert any(c["table"] == "product_diff_result" for c in reader.fetch_calls)
    assert any(c["table"] == "staging_item" for c in reader.fetch_calls)


def test_cli_non_demo_runs_job_with_live_reader(monkeypatch) -> None:
    """DATABASE_URL ありなら exit 3 固定せず Job を起動する。"""

    from dataclasses import replace

    from batch.application.import_summary import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings as scaffold_settings
    from batch.infrastructure.db import ScaffoldDbReader, ScaffoldDbWriter

    reader = ScaffoldDbReader()
    reader.backend = "postgres"

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(
            scaffold_settings(),
            database_url="postgresql://localhost:5432/gift",
        ),
    )
    monkeypatch.setattr(cli, "create_db_writer", lambda _url: ScaffoldDbWriter())
    monkeypatch.setattr(cli, "resolve_job_db_reader", lambda **_kwargs: reader)
    monkeypatch.setattr(
        cli,
        "create_job_run_tracker",
        lambda **_kwargs: __import__(
            "batch.application.job_run", fromlist=["ScaffoldJobRunTracker"]
        ).ScaffoldJobRunTracker(),
    )
    monkeypatch.setattr(
        cli,
        "create_batch_observability_writers",
        lambda **_kwargs: __import__(
            "batch.application.observability", fromlist=["create_batch_observability_writers"]
        ).create_batch_observability_writers(scaffold_demo=True, database_url=None),
    )

    code = cli.main(["--job-run-id", "wave-g-run", "--batch-run-id", "missing-run"])
    # missing batch_run_log → failed (exit 1). Important: Job started (not exit-2/old exit-3).
    assert code == 1
    assert reader.fetch_calls


def test_scaffold_demo_job_succeeds() -> None:
    result = build_scaffold_demo_job().run(
        job_run_id="scaffold-import-summary-run",
        source_api="item_search",
        batch_run_id="scaffold-import-summary-run",
        now=_NOW,
    )
    assert result.status == "succeeded"
    assert result.insert_applied is True


def test_resolve_source_api_accepts_enum() -> None:
    assert resolve_source_api("item_search") == "item_search"
    assert resolve_source_api(" item_ranking ") == "item_ranking"


def test_config_keys_loadable_via_scaffold_and_loader() -> None:
    settings = scaffold_batch_settings()
    assert settings.batch_import_summary_source_api is None
    assert settings.batch_import_summary_batch_run_id is None

    loaded = load_batch_settings(
        environ={
            "APP_ENV": "dev",
            "OBJECT_STORAGE_BUCKET": "raw-dev",
            "BATCH_IMPORT_SUMMARY_SOURCE_API": "genre_search",
            "BATCH_IMPORT_SUMMARY_BATCH_RUN_ID": "run-override",
        }
    )
    assert loaded.batch_import_summary_source_api == "genre_search"
    assert loaded.batch_import_summary_batch_run_id == "run-override"
    assert "genre_search" in repr(loaded)
    assert "run-override" in repr(loaded)


def test_env_keys_registered() -> None:
    from batch.config import BATCH_ENV_KEYS

    assert "BATCH_IMPORT_SUMMARY_SOURCE_API" in BATCH_ENV_KEYS
    assert "BATCH_IMPORT_SUMMARY_BATCH_RUN_ID" in BATCH_ENV_KEYS


def test_fixture_and_printed_output_have_no_secret_like_values(capsys) -> None:
    forbidden = (
        "sk-",
        "openai_api_key",
        "api_key",
        "bearer ",
        "password",
        "secret_token",
        "postgresql://",
        "DATABASE_URL",
    )
    repos, _ = _repos()
    _run(repos)
    for log in repos.error_logs + repos.phase_logs:
        text = str(log).lower()
        for token in forbidden:
            assert token not in text

    assert main(["--scaffold-demo", "--job-run-id", "sec-check"]) == 0
    printed = capsys.readouterr().out.lower()
    for token in forbidden:
        assert token not in printed


def test_item_search_diff_status_counts_match_product_diff_result() -> None:
    """§16 No.5: item_search の diff_status 別件数が product_diff_result と整合する。"""
    repos, _ = _repos(
        source_api="item_search",
        diffs=[
            ProductDiffRow(
                batch_run_id=_RUN, source_api="item_search", diff_status="new"
            ),
            ProductDiffRow(
                batch_run_id=_RUN, source_api="item_search", diff_status="new"
            ),
            ProductDiffRow(
                batch_run_id=_RUN, source_api="item_search", diff_status="updated"
            ),
            ProductDiffRow(
                batch_run_id=_RUN, source_api="item_search", diff_status="updated"
            ),
            ProductDiffRow(
                batch_run_id=_RUN, source_api="item_search", diff_status="updated"
            ),
            ProductDiffRow(
                batch_run_id=_RUN, source_api="item_search", diff_status="unchanged"
            ),
            ProductDiffRow(
                batch_run_id=_RUN, source_api="item_search", diff_status="unavailable"
            ),
            ProductDiffRow(
                batch_run_id=_RUN, source_api="item_search", diff_status="unavailable"
            ),
            ProductDiffRow(
                batch_run_id=_RUN, source_api="item_search", diff_status="unavailable"
            ),
            ProductDiffRow(
                batch_run_id=_RUN, source_api="item_search", diff_status="unavailable"
            ),
        ],
    )
    result = _run(repos, source_api="item_search")
    assert result.status == "succeeded"
    row = repos.summary_rows[0]
    assert row.new_count == 2
    assert row.updated_count == 3
    assert row.unchanged_count == 1
    assert row.unavailable_count == 4


def test_api_call_log_item_count_sum_matches_fetched_count() -> None:
    """§16 No.7: fetched_count が api_call_log.item_count 合計と整合する（正本）。"""
    repos, _ = _repos(
        source_api="item_search",
        api_calls=[
            ApiCallLogRow(batch_run_id=_RUN, source_api="item_search", item_count=10),
            ApiCallLogRow(batch_run_id=_RUN, source_api="item_search", item_count=15),
            ApiCallLogRow(batch_run_id=_RUN, source_api="item_search", item_count=8),
        ],
    )
    result = _run(repos, source_api="item_search")
    assert result.status == "succeeded"
    row = repos.summary_rows[0]
    assert row.fetched_count == 33


def test_attribute_search_source_api_is_valid() -> None:
    """attribute_search が valid source_api として扱える。"""
    repos, _ = _repos(
        source_api="attribute_search",
        api_calls=[
            ApiCallLogRow(
                batch_run_id=_RUN, source_api="attribute_search", item_count=20
            )
        ],
        diffs=[
            ProductDiffRow(
                batch_run_id=_RUN, source_api="attribute_search", diff_status="new"
            ),
            ProductDiffRow(
                batch_run_id=_RUN, source_api="attribute_search", diff_status="updated"
            ),
        ],
    )
    result = _run(repos, source_api="attribute_search")
    assert result.status == "succeeded"
    row = repos.summary_rows[0]
    assert row.source_api == "attribute_search"
    assert row.fetched_count == 20
    assert row.new_count == 1
    assert row.updated_count == 1


def test_source_defaults_to_rakuten() -> None:
    """source が 'rakuten' 固定である。"""
    repos, _ = _repos()
    result = _run(repos)
    assert result.status == "succeeded"
    row = repos.summary_rows[0]
    assert row.source == "rakuten"


def test_multiple_runs_with_different_source_api_insert_separately() -> None:
    """異なる source_api の Run は独立して INSERT できる。"""
    repos1, _ = _repos(source_api="item_search", batch_run_id="run-01")
    result1 = _run(repos1, job_run_id="run-01", source_api="item_search")
    assert result1.status == "succeeded"

    repos2, _ = _repos(source_api="item_ranking", batch_run_id="run-01")
    result2 = _run(repos2, job_run_id="run-01", source_api="item_ranking")
    assert result2.status == "succeeded"

    assert len(repos1.summary_rows) == 1
    assert len(repos2.summary_rows) == 1
    assert repos1.summary_rows[0].source_api == "item_search"
    assert repos2.summary_rows[0].source_api == "item_ranking"


def test_different_batch_run_id_allows_new_insert() -> None:
    """異なる batch_run_id では新規 INSERT できる。"""
    repos, _ = _repos(batch_run_id="run-A")
    result1 = _run(repos, job_run_id="run-A")
    assert result1.status == "succeeded"
    assert result1.insert_applied is True

    repos2, _ = _repos(batch_run_id="run-B")
    result2 = _run(repos2, job_run_id="run-B")
    assert result2.status == "succeeded"
    assert result2.insert_applied is True

    assert len(repos.summary_rows) == 1
    assert len(repos2.summary_rows) == 1


def test_phase_log_only_has_summary_created() -> None:
    """§16 No.9: phase_log が summary_created のみである。"""
    repos, _ = _repos()
    result = _run(repos)
    assert result.status == "succeeded"
    assert len(repos.phase_logs) == 1
    assert repos.phase_logs[0]["phase"] == PHASE_SUMMARY_CREATED
    assert repos.phase_logs[0]["status"] == "succeeded"


def test_skip_fail_counts_are_recorded() -> None:
    """skipped_count / failed_count が正しく記録される。"""
    repos, _ = _repos(skip_fail=SkipFailCounts(skipped_count=5, failed_count=2))
    result = _run(repos)
    assert result.status == "succeeded"
    row = repos.summary_rows[0]
    assert row.skipped_count == 5
    assert row.failed_count == 2
