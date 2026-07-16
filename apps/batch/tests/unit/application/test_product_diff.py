"""Unit tests for BATCH-006 商品差分判定（仕様書 §16 最小観点）."""

from __future__ import annotations

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
    assert {c["table"] for c in db.write_calls}.isdisjoint(_FORBIDDEN_TABLES)


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
    repos, _ = _repos(
        staging=[_staging(normalized_hash=_HASH_A)],
        items=[_item(normalized_hash=_HASH_A, item_name="Keep Name", active_status="active")],
    )
    snapshot = dict(repos.items[("rakuten", "shop:gift-1")])
    job = ProductDiffJob(repositories=repos)

    result = job.run(job_run_id="run-same")

    assert result.status == "succeeded"
    assert result.diff_unchanged_count == 1
    row = repos.product_diff_results[("run-same", "shop:gift-1")]
    assert row["diff_status"] == "unchanged"
    assert row["old_hash"] == _HASH_A
    assert row["new_hash"] == _HASH_A
    # Item 業務列は不変
    assert repos.items[("rakuten", "shop:gift-1")] == snapshot


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
    written = {c["table"] for c in db.write_calls}
    assert written.isdisjoint(_FORBIDDEN_TABLES)
    assert "product_diff_result" in written


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
