"""Unit tests for BATCH-006 商品差分判定（仕様書 §16 unit 観点）."""

from __future__ import annotations

import json
import re

import pytest

from batch.application.job_run import ScaffoldJobRunTracker
from batch.application.product_diff import (
    BATCH_ID,
    PRODUCT_DIFF_PHASES,
    ItemSeed,
    ProductDiffJob,
    ProductDiffRepositories,
    StagingItemSeed,
    compare_staging_to_item,
)
from batch.application.product_diff.compare import ProductDiffCompareError
from batch.infrastructure.db import ScaffoldDbWriter
from batch.infrastructure.logger import ScaffoldBatchLogger

_HASH_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
_HASH_B = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
_HASH_C = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"

_FORBIDDEN_TABLES = frozenset(
    {
        "item",
        "item_image",
        "item_active_status",
        "item_review_summary",
    }
)

# product_diff_result が持ってよい列（source / item_id は不採用・#526）
_PRODUCT_DIFF_RESULT_ALLOWED_KEYS = frozenset(
    {
        "product_diff_result_id",
        "batch_run_id",
        "staging_item_id",
        "external_item_code",
        "old_hash",
        "new_hash",
        "diff_status",
        "judged_at",
        "updated_at",
    }
)

# §16 No.13: fixture / logs に実token風が残らないこと
_SECRET_PATTERN = re.compile(
    r"(?i)(sk-[a-z0-9]{10,}|bearer\s+[a-z0-9\-._~+/]+=*|ghp_[a-z0-9]{20,}|"
    r"xox[baprs]-[a-z0-9-]+|supabase\.co/.{20,})"
)
_FORBIDDEN_SECRET_FIELD_NAMES = (
    "api_key",
    "access_token",
    "refresh_token",
    "authorization",
    "client_secret",
    "database_url",
    "object_storage_secret_key",
    "password",
)


def _staging(
    *,
    staging_item_id: str = "si_1",
    external_item_code: str = "shop:gift-1",
    normalized_hash: str | None = _HASH_A,
    item_name: str | None = "Gift A",
    item_url: str | None = "https://item.example/shop/gift-1",
    price: int | None = 2500,
    availability: int | None = 1,
    diff_status: str | None = None,
    validation_failed: bool = False,
    fetch_unavailable: bool = False,
) -> StagingItemSeed:
    return StagingItemSeed(
        staging_item_id=staging_item_id,
        source="rakuten",
        external_item_code=external_item_code,
        normalized_hash=normalized_hash,
        item_name=item_name,
        item_url=item_url,
        price=price,
        availability=availability,
        diff_status=diff_status,
        validation_failed=validation_failed,
        fetch_unavailable=fetch_unavailable,
    )


def _item(
    *,
    external_item_code: str = "shop:gift-1",
    normalized_hash: str | None = _HASH_A,
    item_name: str = "Gift A",
    active_status: str = "active",
) -> ItemSeed:
    return ItemSeed(
        source="rakuten",
        external_item_code=external_item_code,
        normalized_hash=normalized_hash,
        item_id=f"it_{external_item_code.replace(':', '_')}",
        item_name=item_name,
        active_status=active_status,
    )


def _repos(
    *,
    staging: list[StagingItemSeed] | None = None,
    items: list[ItemSeed] | None = None,
) -> tuple[ProductDiffRepositories, ScaffoldDbWriter]:
    db = ScaffoldDbWriter()
    repos = ProductDiffRepositories(
        db_writer=db,
        seed_staging=list(staging or [_staging()]),
        seed_items=list(items or []),
    )
    return repos, db


def test_diff_status_new_when_item_missing() -> None:
    repos, db = _repos(staging=[_staging()], items=[])
    job = ProductDiffJob(repositories=repos)

    result = job.run(job_run_id="run-new")

    assert result.batch_id == BATCH_ID
    assert result.status == "succeeded"
    assert result.diff_new_count == 1
    assert result.diff_updated_count == 0
    key = ("run-new", "shop:gift-1")
    row = repos.product_diff_results[key]
    assert row["diff_status"] == "new"
    assert row["old_hash"] is None
    assert row["new_hash"] == _HASH_A
    assert "source" not in row
    assert "item_id" not in row
    assert set(PRODUCT_DIFF_PHASES).issubset(set(result.completed_phases))
    written = {c["table"] for c in db.write_calls} | {c["table"] for c in db.upsert_calls}
    assert written.isdisjoint(_FORBIDDEN_TABLES)
    assert "product_diff_result" in {c["table"] for c in db.upsert_calls}


def test_diff_status_updated_when_hash_differs() -> None:
    repos, _ = _repos(
        staging=[_staging(normalized_hash=_HASH_B)],
        items=[_item(normalized_hash=_HASH_A)],
    )
    job = ProductDiffJob(repositories=repos)

    result = job.run(job_run_id="run-upd")

    assert result.status == "succeeded"
    assert result.diff_updated_count == 1
    row = repos.product_diff_results[("run-upd", "shop:gift-1")]
    assert row["diff_status"] == "updated"
    assert row["old_hash"] == _HASH_A
    assert row["new_hash"] == _HASH_B


def test_diff_status_unchanged_when_hash_matches() -> None:
    """§16 No.3: hash 一致で unchanged。item 業務列（name / active_status 等）は不変。"""

    repos, db = _repos(
        staging=[_staging(normalized_hash=_HASH_A)],
        items=[_item(normalized_hash=_HASH_A, item_name="Keep Name", active_status="active")],
    )
    item_key = ("rakuten", "shop:gift-1")
    snapshot = dict(repos.items[item_key])
    job = ProductDiffJob(repositories=repos)

    result = job.run(job_run_id="run-same")

    assert result.status == "succeeded"
    assert result.diff_unchanged_count == 1
    row = repos.product_diff_results[("run-same", "shop:gift-1")]
    assert row["diff_status"] == "unchanged"
    assert row["old_hash"] == _HASH_A
    assert row["new_hash"] == _HASH_A
    # Item 業務列は不変（全体スナップショット + 明示列）
    assert repos.items[item_key] == snapshot
    assert repos.items[item_key]["item_name"] == "Keep Name"
    assert repos.items[item_key]["active_status"] == "active"
    assert repos.items[item_key]["normalized_hash"] == _HASH_A
    assert ({c["table"] for c in db.write_calls} | {c["table"] for c in db.upsert_calls}).isdisjoint(_FORBIDDEN_TABLES)


def test_diff_status_unavailable_availability_zero() -> None:
    repos, _ = _repos(
        staging=[_staging(availability=0)],
        items=[_item()],
    )
    job = ProductDiffJob(repositories=repos)

    result = job.run(job_run_id="run-unavail")

    assert result.status == "succeeded"
    assert result.diff_unavailable_count == 1
    row = repos.product_diff_results[("run-unavail", "shop:gift-1")]
    assert row["diff_status"] == "unavailable"
    assert row["new_hash"] == _HASH_A


def test_diff_status_unavailable_missing_required_staging_field() -> None:
    """§16 No.4 / §18.1 No.9 (a): Staging 必須項目欠落 → unavailable。"""

    judgment = compare_staging_to_item(
        staging=_staging(item_name=None),
        item=_item(),
    )
    assert judgment.diff_status == "unavailable"
    assert judgment.old_hash == _HASH_A
    assert judgment.new_hash == _HASH_A

    repos, _ = _repos(
        staging=[_staging(item_url="")],
        items=[_item()],
    )
    result = ProductDiffJob(repositories=repos).run(job_run_id="run-unavail-missing")
    assert result.status == "succeeded"
    assert result.diff_unavailable_count == 1
    row = repos.product_diff_results[("run-unavail-missing", "shop:gift-1")]
    assert row["diff_status"] == "unavailable"


def test_unavailable_takes_priority_over_new() -> None:
    """Item 未存在でも unavailable 条件が優先（§9.2）。"""

    judgment = compare_staging_to_item(
        staging=_staging(availability=0),
        item=None,
    )
    assert judgment.diff_status == "unavailable"
    assert judgment.old_hash is None


def test_item_tables_not_written() -> None:
    repos, db = _repos(
        staging=[
            _staging(staging_item_id="si_a", external_item_code="shop:a", normalized_hash=_HASH_A),
            _staging(staging_item_id="si_b", external_item_code="shop:b", normalized_hash=_HASH_B),
        ],
        items=[_item(external_item_code="shop:b", normalized_hash=_HASH_A)],
    )
    before_items = {k: dict(v) for k, v in repos.items.items()}
    job = ProductDiffJob(repositories=repos)

    result = job.run(job_run_id="run-boundary")

    assert result.status == "succeeded"
    assert result.written_item_rows == []
    assert result.written_item_image_rows == []
    assert result.written_active_status_rows == []
    assert repos.items == before_items
    written = {c["table"] for c in db.write_calls} | {c["table"] for c in db.upsert_calls}
    assert written.isdisjoint(_FORBIDDEN_TABLES)
    assert "product_diff_result" in {c["table"] for c in db.upsert_calls}


def test_hash_not_recalculated() -> None:
    repos, _ = _repos(
        staging=[_staging(normalized_hash=_HASH_C)],
        items=[],
    )
    original = repos.staging_items["si_1"]["normalized_hash"]
    job = ProductDiffJob(repositories=repos)

    result = job.run(job_run_id="run-hash")

    assert result.status == "succeeded"
    assert result.hash_recalculate_calls == []
    assert repos.hash_recalculate_calls == []
    assert repos.staging_items["si_1"]["normalized_hash"] == original
    assert repos.product_diff_results[("run-hash", "shop:gift-1")]["new_hash"] == original


def test_idempotent_upsert_on_same_run_key() -> None:
    repos, _ = _repos(staging=[_staging()], items=[])
    job = ProductDiffJob(repositories=repos)

    first = job.run(job_run_id="run-idem")
    assert first.status == "succeeded"
    first_row = dict(repos.product_diff_results[("run-idem", "shop:gift-1")])

    # force で再判定 → UNIQUE upsert 上書き
    second = job.run(job_run_id="run-idem", force=True)
    assert second.status == "succeeded"
    second_row = repos.product_diff_results[("run-idem", "shop:gift-1")]

    assert len(repos.product_diff_results) == 1
    assert second_row["product_diff_result_id"] == first_row["product_diff_result_id"]
    assert second_row["diff_status"] == "new"
    assert second.product_diff_upsert_count == 1


def test_staging_diff_status_sync_on_by_default() -> None:
    repos, db = _repos(staging=[_staging(diff_status=None)], items=[])
    job = ProductDiffJob(repositories=repos)

    result = job.run(job_run_id="run-sync")

    assert result.status == "succeeded"
    assert result.staging_diff_status_sync_count == 1
    assert repos.staging_items["si_1"]["diff_status"] == "new"
    assert any(c["table"] == "staging_item" for c in db.write_calls)


def test_staging_diff_status_sync_can_be_disabled() -> None:
    repos, db = _repos(staging=[_staging(diff_status=None)], items=[])
    job = ProductDiffJob(repositories=repos)

    result = job.run(job_run_id="run-nosync", sync_staging_diff_status=False)

    assert result.status == "succeeded"
    assert result.staging_diff_status_sync_count == 0
    assert repos.staging_items["si_1"]["diff_status"] is None
    assert ("run-nosync", "shop:gift-1") in repos.product_diff_results
    assert not any(c["table"] == "staging_item" for c in db.write_calls)


def test_null_hash_fails_compare_and_is_excluded_from_plan() -> None:
    try:
        compare_staging_to_item(staging=_staging(normalized_hash=None), item=None)
        raise AssertionError("expected ProductDiffCompareError")
    except ProductDiffCompareError as exc:
        assert exc.code == "GRS-BAT-007"

    repos, _ = _repos(staging=[_staging(normalized_hash=None)], items=[])
    run = ProductDiffJob(repositories=repos).run(
        job_run_id="run-null-hash",
        staging_item_ids=("si_1",),
        force=True,
    )
    # hash NULL は選定除外 → empty plan（seed はあるが eligible 0 → noop succeeded）
    assert run.planned_staging_count == 0
    assert repos.product_diff_results == {}


def test_invalid_hash_in_process_fails_row() -> None:
    """load 後に不正 hash だと当該行失敗（判定行なし）."""

    staging = _staging(
        normalized_hash="zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"
    )
    try:
        compare_staging_to_item(staging=staging, item=None)
        raise AssertionError("expected ProductDiffCompareError")
    except ProductDiffCompareError as exc:
        assert exc.code == "GRS-BAT-007"

    # Job: 選定時は valid、process 中に load で不正 hash を返す
    class _MutatingRepos(ProductDiffRepositories):
        def load_staging(self, *, staging_item_id: str):  # type: ignore[override]
            seed = super().load_staging(staging_item_id=staging_item_id)
            return StagingItemSeed(
                staging_item_id=seed.staging_item_id,
                source=seed.source,
                external_item_code=seed.external_item_code,
                normalized_hash="short",
                item_name=seed.item_name,
                item_url=seed.item_url,
                price=seed.price,
                availability=seed.availability,
                diff_status=seed.diff_status,
            )

    bad_repos = _MutatingRepos(
        db_writer=ScaffoldDbWriter(),
        seed_staging=[_staging()],
        seed_items=[],
    )
    result = ProductDiffJob(repositories=bad_repos).run(job_run_id="run-bad-hash")
    assert result.status == "failed"
    assert "GRS-BAT-007" in result.error_codes
    assert bad_repos.product_diff_results == {}


def test_concurrent_start_rejected() -> None:
    tracker = ScaffoldJobRunTracker()
    tracker.start(batch_id=BATCH_ID, job_run_id="already-running")
    repos, _ = _repos()
    job = ProductDiffJob(repositories=repos, job_run_tracker=tracker)

    result = job.run(job_run_id="run-concurrent")

    assert result.status == "failed"
    assert "GRS-BAT-003" in result.error_codes
    assert repos.product_diff_results == {}


def test_selection_skips_already_judged_unless_force() -> None:
    repos, _ = _repos(
        staging=[_staging(diff_status="new")],
        items=[],
    )
    job = ProductDiffJob(repositories=repos)

    noop = job.run(job_run_id="run-skip")
    assert noop.status == "succeeded"
    assert noop.planned_staging_count == 0
    assert repos.product_diff_results == {}

    forced = job.run(job_run_id="run-force", force=True)
    assert forced.status == "succeeded"
    assert forced.planned_staging_count == 1
    assert ("run-force", "shop:gift-1") in repos.product_diff_results


def test_product_diff_result_is_canonical_when_staging_sync_off() -> None:
    """§16 No.7: 判定正本は product_diff_result。Staging のみ更新しても正本扱いにしない。"""

    repos, db = _repos(staging=[_staging(diff_status=None)], items=[])
    job = ProductDiffJob(repositories=repos)

    result = job.run(job_run_id="run-canonical", sync_staging_diff_status=False)

    assert result.status == "succeeded"
    assert result.staging_diff_status_sync_count == 0
    key = ("run-canonical", "shop:gift-1")
    assert key in repos.product_diff_results
    assert repos.product_diff_results[key]["diff_status"] == "new"
    # sync OFF のため Staging は未更新のまま
    assert repos.staging_items["si_1"]["diff_status"] is None
    assert not any(c["table"] == "staging_item" for c in db.write_calls)

    # Staging だけ別値に書き換えても、正本は product_diff_result
    repos.staging_items["si_1"]["diff_status"] = "updated"
    assert repos.product_diff_results[key]["diff_status"] == "new"
    assert (
        repos.product_diff_results[key]["diff_status"]
        != repos.staging_items["si_1"]["diff_status"]
    )


def test_product_diff_result_rows_omit_source_and_item_id() -> None:
    """§16 No.10: product_diff_result 行に source / item_id キーを持たない。"""

    repos, _ = _repos(
        staging=[
            _staging(
                staging_item_id="si_new",
                external_item_code="shop:new",
                normalized_hash=_HASH_A,
            ),
            _staging(
                staging_item_id="si_upd",
                external_item_code="shop:upd",
                normalized_hash=_HASH_B,
            ),
            _staging(
                staging_item_id="si_same",
                external_item_code="shop:same",
                normalized_hash=_HASH_A,
            ),
            _staging(
                staging_item_id="si_unavail",
                external_item_code="shop:unavail",
                normalized_hash=_HASH_C,
                availability=0,
            ),
        ],
        items=[
            _item(external_item_code="shop:upd", normalized_hash=_HASH_A),
            _item(external_item_code="shop:same", normalized_hash=_HASH_A),
            _item(external_item_code="shop:unavail", normalized_hash=_HASH_A),
        ],
    )
    result = ProductDiffJob(repositories=repos).run(job_run_id="run-cols")

    assert result.status == "succeeded"
    assert len(repos.product_diff_results) == 4
    for row in repos.product_diff_results.values():
        assert "source" not in row
        assert "item_id" not in row
        assert set(row.keys()).issubset(_PRODUCT_DIFF_RESULT_ALLOWED_KEYS)


def test_partial_success_one_row_fails_grs_bat_002() -> None:
    """§16 No.11: 一部行失敗・他行成功 → partially_succeeded + GRS-BAT-002。"""

    class _FailOneRepos(ProductDiffRepositories):
        def load_staging(self, *, staging_item_id: str):  # type: ignore[override]
            seed = super().load_staging(staging_item_id=staging_item_id)
            if seed.external_item_code != "shop:bad":
                return seed
            # 選定時は valid、process 中に不正 hash を返して当該行のみ失敗させる
            return StagingItemSeed(
                staging_item_id=seed.staging_item_id,
                source=seed.source,
                external_item_code=seed.external_item_code,
                normalized_hash="short",
                item_name=seed.item_name,
                item_url=seed.item_url,
                price=seed.price,
                availability=seed.availability,
                diff_status=seed.diff_status,
                validation_failed=seed.validation_failed,
                fetch_unavailable=seed.fetch_unavailable,
            )

    repos = _FailOneRepos(
        db_writer=ScaffoldDbWriter(),
        seed_staging=[
            _staging(
                staging_item_id="si_ok",
                external_item_code="shop:ok",
                normalized_hash=_HASH_A,
            ),
            _staging(
                staging_item_id="si_bad",
                external_item_code="shop:bad",
                normalized_hash=_HASH_B,
            ),
        ],
        seed_items=[],
    )
    result = ProductDiffJob(repositories=repos).run(job_run_id="run-partial")

    assert result.status == "partially_succeeded"
    assert "GRS-BAT-002" in result.error_codes
    assert "GRS-BAT-007" in result.error_codes
    assert "shop:ok" in result.succeeded_external_codes
    assert "shop:bad" in result.failed_external_codes
    assert ("run-partial", "shop:ok") in repos.product_diff_results
    assert ("run-partial", "shop:bad") not in repos.product_diff_results
    assert repos.product_diff_results[("run-partial", "shop:ok")]["diff_status"] == "new"
    assert any(e["code"] == "GRS-BAT-007" for e in repos.error_logs)


def test_secret_non_containment_in_fixtures_and_error_logs() -> None:
    """§16 No.13: fixture / error_logs / logger 属性に認証情報・token 風文字列がない。"""

    fixture_blob = json.dumps(
        {
            "staging": _staging().__dict__,
            "item": _item().__dict__,
        },
        ensure_ascii=False,
        default=str,
    )
    assert _SECRET_PATTERN.search(fixture_blob) is None
    for name in _FORBIDDEN_SECRET_FIELD_NAMES:
        assert name not in fixture_blob.lower()

    class _FailBadRepos(ProductDiffRepositories):
        def load_staging(self, *, staging_item_id: str):  # type: ignore[override]
            seed = super().load_staging(staging_item_id=staging_item_id)
            if seed.external_item_code != "shop:bad":
                return seed
            return StagingItemSeed(
                staging_item_id=seed.staging_item_id,
                source=seed.source,
                external_item_code=seed.external_item_code,
                normalized_hash="short",
                item_name=seed.item_name,
                item_url=seed.item_url,
                price=seed.price,
                availability=seed.availability,
                diff_status=seed.diff_status,
            )

    logger = ScaffoldBatchLogger()
    # process 時失敗注入で error_logs / logger を検証（選定時は valid hash）
    fail_repos = _FailBadRepos(
        db_writer=ScaffoldDbWriter(),
        seed_staging=[
            _staging(
                staging_item_id="si_ok",
                external_item_code="shop:ok",
                normalized_hash=_HASH_A,
            ),
            _staging(
                staging_item_id="si_bad",
                external_item_code="shop:bad",
                normalized_hash=_HASH_B,
            ),
        ],
        seed_items=[],
    )
    result = ProductDiffJob(repositories=fail_repos, logger=logger).run(
        job_run_id="run-secret-check"
    )
    assert result.status == "partially_succeeded"

    for entry in fail_repos.error_logs:
        text = json.dumps(entry, ensure_ascii=False, default=str)
        assert _SECRET_PATTERN.search(text) is None
        for name in _FORBIDDEN_SECRET_FIELD_NAMES:
            assert name not in text.lower()
    for code in result.error_codes:
        assert _SECRET_PATTERN.search(code) is None
    for record in logger.records:
        payload = json.dumps(
            {
                "event": record.event,
                "attributes": record.attributes,
                "job_run_id": record.context.job_run_id,
                "trace_id": record.context.trace_id,
            },
            ensure_ascii=False,
            default=str,
        )
        assert _SECRET_PATTERN.search(payload) is None
        for name in _FORBIDDEN_SECRET_FIELD_NAMES:
            assert name not in payload.lower()


def test_list_eligible_staging_uses_db_reader_when_injected() -> None:
    """Wave B: DbReader 注入時は seed ではなく SELECT 経路を使う。"""

    from batch.infrastructure.db import ScaffoldDbReader

    reader = ScaffoldDbReader()
    reader.seed(
        "staging_item",
        (
            {
                "staging_item_id": "si_a",
                "source": "rakuten",
                "external_item_code": "shop:a",
                "normalized_hash": _HASH_A,
                "item_name": "A",
                "item_url": "https://item.example/a",
                "price": 1000,
                "availability": 1,
                "diff_status": None,
            },
            {
                "staging_item_id": "si_done",
                "source": "rakuten",
                "external_item_code": "shop:done",
                "normalized_hash": _HASH_B,
                "item_name": "Done",
                "item_url": "https://item.example/done",
                "price": 2000,
                "availability": 1,
                "diff_status": "new",
            },
            {
                "staging_item_id": "si_nohash",
                "source": "rakuten",
                "external_item_code": "shop:nohash",
                "normalized_hash": None,
                "item_name": "NoHash",
                "item_url": None,
                "price": None,
                "availability": None,
                "diff_status": None,
            },
        ),
    )
    repos = ProductDiffRepositories(db_writer=ScaffoldDbWriter(), db_reader=reader)

    selected = repos.list_eligible_staging(max_items=10)
    assert [s.staging_item_id for s in selected] == ["si_a"]
    assert reader.fetch_calls
    assert reader.fetch_calls[0]["table"] == "staging_item"


def test_resolve_item_uses_db_reader_when_injected() -> None:
    from batch.infrastructure.db import ScaffoldDbReader

    reader = ScaffoldDbReader()
    reader.seed(
        "item",
        (
            {
                "item_id": "it_1",
                "source": "rakuten",
                "external_item_code": "shop:a",
                "normalized_hash": _HASH_A,
                "item_name": "A",
                "active_status": "active",
            },
        ),
    )
    repos = ProductDiffRepositories(db_writer=ScaffoldDbWriter(), db_reader=reader)
    found = repos.resolve_item(source="rakuten", external_item_code="shop:a")
    assert found is not None
    assert found.item_id == "it_1"
    assert repos.resolve_item(source="rakuten", external_item_code="missing") is None


def test_cli_non_demo_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    from dataclasses import replace

    from batch.application.product_diff import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(scaffold_batch_settings(), database_url=None),
    )
    assert cli.main(["--job-run-id", "no-db"]) == 2


def test_batch_run_id_separates_product_diff_write_from_job_run_id() -> None:
    """product_diff_result の batch_run_id は共有 pipeline、tracker は葉 job_run_id。"""

    staging = [
        StagingItemSeed(
            staging_item_id="si_sep",
            source="rakuten",
            external_item_code="shop:sep",
            normalized_hash=_HASH_A,
            item_name="Sep",
            item_url="https://item.example/shop/sep",
            price=1000,
            availability=1,
            diff_status=None,
        )
    ]
    repos = ProductDiffRepositories(
        db_writer=ScaffoldDbWriter(),
        seed_staging=staging,
        seed_items=[],
    )
    tracker = ScaffoldJobRunTracker()
    job = ProductDiffJob(repositories=repos, job_run_tracker=tracker)
    pipeline = "pipeline-006"
    leaf = "leaf-006"
    repos.bind_run(batch_run_id=pipeline)

    result = job.run(job_run_id=leaf, batch_run_id=pipeline)

    assert result.status == "succeeded"
    assert result.job_run_id == leaf
    key = (pipeline, "shop:sep")
    assert key in repos.product_diff_results
    assert repos.product_diff_results[key]["batch_run_id"] == pipeline
    assert (leaf, "shop:sep") not in repos.product_diff_results
    assert any(
        getattr(r, "job_run_id", None) == leaf for r in tracker.records
    )


def test_cli_batch_run_id_fallback_to_job_run_id() -> None:
    from batch.application.product_diff.__main__ import _resolve_business_run_id

    assert _resolve_business_run_id(job_run_id="leaf", batch_run_id="") == "leaf"
    assert (
        _resolve_business_run_id(job_run_id="leaf", batch_run_id="pipeline") == "pipeline"
    )

