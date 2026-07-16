"""Unit tests for BATCH-007 Item反映（仕様書 §16 unit 観点）."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from batch.application.item_apply import (
    BATCH_ID,
    ITEM_APPLY_PHASES,
    ItemApplyJob,
    ItemApplyRepositories,
    ItemSeed,
    ProductDiffResultSeed,
    StagingImageSeed,
    StagingItemSeed,
)
from batch.application.job_run import ScaffoldJobRunTracker
from batch.infrastructure.db import ScaffoldDbWriter

# §16 No.12: unit 代替で非更新を確認する境界テーブル
_FORBIDDEN_BOUNDARY_TABLES = frozenset(
    {
        "item_popularity_signal",
        "item_generation_queue",
        "product_diff_result",
    }
)

_HASH_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
_HASH_B = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

_SECRET_PATTERN = re.compile(
    r"(?i)(sk-[a-z0-9]{10,}|bearer\s+[a-z0-9\-._~+/]+=*|ghp_[a-z0-9]{20,}|"
    r"xox[baprs]-[a-z0-9-]+|supabase\.co/.{20,})"
)


def _diff(
    *,
    product_diff_result_id: str = "pdr_1",
    batch_run_id: str = "diff-run-1",
    staging_item_id: str = "si_1",
    external_item_code: str = "shop:gift-1",
    diff_status: str = "new",
    old_hash: str | None = None,
    new_hash: str | None = _HASH_A,
) -> ProductDiffResultSeed:
    return ProductDiffResultSeed(
        product_diff_result_id=product_diff_result_id,
        batch_run_id=batch_run_id,
        staging_item_id=staging_item_id,
        external_item_code=external_item_code,
        diff_status=diff_status,  # type: ignore[arg-type]
        old_hash=old_hash,
        new_hash=new_hash,
    )


def _staging(
    *,
    staging_item_id: str = "si_1",
    external_item_code: str = "shop:gift-1",
    normalized_hash: str | None = _HASH_A,
    item_name: str | None = "Gift A",
    price: int | None = 2500,
    item_url: str | None = "https://item.example/shop/gift-1",
    review_average: float | None = 4.2,
    review_count: int | None = 12,
) -> StagingItemSeed:
    return StagingItemSeed(
        staging_item_id=staging_item_id,
        source="rakuten",
        external_item_code=external_item_code,
        normalized_hash=normalized_hash,
        item_name=item_name,
        price=price,
        item_url=item_url,
        review_average=review_average,
        review_count=review_count,
    )


def _item(
    *,
    external_item_code: str = "shop:gift-1",
    normalized_hash: str | None = _HASH_A,
    item_name: str = "Gift A",
    active_status: str = "active",
    is_active: bool = True,
) -> ItemSeed:
    return ItemSeed(
        source="rakuten",
        external_item_code=external_item_code,
        normalized_hash=normalized_hash,
        item_id=f"it_{external_item_code.replace(':', '_')}",
        item_name=item_name,
        active_status=active_status,
        is_active=is_active,
        last_checked_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _repos(
    *,
    diffs: list[ProductDiffResultSeed] | None = None,
    staging: list[StagingItemSeed] | None = None,
    images: list[StagingImageSeed] | None = None,
    items: list[ItemSeed] | None = None,
) -> tuple[ItemApplyRepositories, ScaffoldDbWriter]:
    db = ScaffoldDbWriter()
    repos = ItemApplyRepositories(
        db_writer=db,
        seed_diffs=list(diffs or [_diff()]),
        seed_staging=list(staging or [_staging()]),
        seed_images=list(images or []),
        seed_items=list(items or []),
    )
    return repos, db


def test_new_inserts_item_images_and_review_with_ddl_default_active_status() -> None:
    images = [
        StagingImageSeed(
            staging_item_id="si_1",
            image_url="https://img.example/a.jpg",
            display_order=0,
            is_primary_candidate=True,
        ),
        StagingImageSeed(
            staging_item_id="si_1",
            image_url="https://img.example/b.jpg",
            display_order=1,
            is_primary_candidate=False,
        ),
    ]
    repos, db = _repos(images=images)
    job = ItemApplyJob(repositories=repos)

    result = job.run(job_run_id="run-new")

    assert result.batch_id == BATCH_ID
    assert result.status == "succeeded"
    assert result.item_upsert_count == 1
    assert result.item_image_sync_count == 1
    assert result.item_review_upsert_count == 1
    assert set(ITEM_APPLY_PHASES).issubset(set(result.completed_phases))

    item = repos.items[("rakuten", "shop:gift-1")]
    assert item["item_name"] == "Gift A"
    assert item["normalized_hash"] == _HASH_A
    assert item["active_status"] == "active"
    assert item["is_active"] is True
    assert item["last_checked_at"] is not None

    item_id = str(item["item_id"])
    synced = repos.item_images[item_id]
    assert set(synced.keys()) == {
        "https://img.example/a.jpg",
        "https://img.example/b.jpg",
    }
    assert sum(1 for r in synced.values() if r["is_primary"]) == 1
    assert synced["https://img.example/a.jpg"]["is_primary"] is True

    review = repos.item_reviews[item_id]
    assert review["review_average"] == 4.2
    assert review["review_count"] == 12

    assert {c["table"] for c in db.write_calls} >= {"item", "item_image", "item_review_summary"}
    assert "product_diff_result" not in {c["table"] for c in db.write_calls}
    assert result.product_diff_write_count == 0
    assert result.hash_recalculate_calls == []


def test_updated_copies_hash_without_touching_active_status() -> None:
    repos, _ = _repos(
        diffs=[
            _diff(
                diff_status="updated",
                old_hash=_HASH_A,
                new_hash=_HASH_B,
            )
        ],
        staging=[_staging(normalized_hash=_HASH_B, item_name="Gift A Updated", price=3000)],
        items=[_item(normalized_hash=_HASH_A, active_status="inactive", is_active=False)],
    )
    key = ("rakuten", "shop:gift-1")
    before_status = repos.items[key]["active_status"]
    before_active = repos.items[key]["is_active"]
    job = ItemApplyJob(repositories=repos)

    result = job.run(job_run_id="run-upd")

    assert result.status == "succeeded"
    assert result.item_upsert_count == 1
    assert repos.items[key]["item_name"] == "Gift A Updated"
    assert repos.items[key]["normalized_hash"] == _HASH_B
    assert repos.items[key]["price"] == 3000
    assert repos.items[key]["active_status"] == before_status == "inactive"
    assert repos.items[key]["is_active"] is before_active is False
    assert result.hash_recalculate_calls == []
    # write payload must not set active_status / is_active
    for row in repos.written_item_rows:
        assert "active_status" not in row
        assert "is_active" not in row


def test_unchanged_touches_last_checked_only_no_images_or_review() -> None:
    repos, db = _repos(
        diffs=[_diff(diff_status="unchanged", old_hash=_HASH_A, new_hash=_HASH_A)],
        staging=[_staging(item_name="Keep Name", review_average=4.9, review_count=99)],
        images=[
            StagingImageSeed(
                staging_item_id="si_1",
                image_url="https://img.example/should-not-apply.jpg",
                is_primary_candidate=True,
            )
        ],
        items=[_item(item_name="Keep Name", active_status="active")],
    )
    key = ("rakuten", "shop:gift-1")
    before = {
        "item_name": repos.items[key]["item_name"],
        "normalized_hash": repos.items[key]["normalized_hash"],
        "active_status": repos.items[key]["active_status"],
        "is_active": repos.items[key]["is_active"],
        "price": repos.items[key]["price"],
    }
    old_checked = repos.items[key]["last_checked_at"]
    job = ItemApplyJob(repositories=repos)

    result = job.run(job_run_id="run-same")

    assert result.status == "succeeded"
    assert result.item_unchanged_touch_count == 1
    assert result.item_upsert_count == 0
    assert result.item_image_sync_count == 0
    assert result.item_review_upsert_count == 0
    assert repos.items[key]["item_name"] == before["item_name"]
    assert repos.items[key]["normalized_hash"] == before["normalized_hash"]
    assert repos.items[key]["active_status"] == before["active_status"]
    assert repos.items[key]["is_active"] is before["is_active"]
    assert repos.items[key]["last_checked_at"] != old_checked
    assert repos.item_images == {}
    assert repos.item_reviews == {}
    assert "item_image" not in {c["table"] for c in db.write_calls}
    assert "item_review_summary" not in {c["table"] for c in db.write_calls}


def test_unavailable_is_fully_skipped() -> None:
    repos, db = _repos(
        diffs=[_diff(diff_status="unavailable", old_hash=_HASH_A, new_hash=_HASH_A)],
        staging=[_staging(item_name="Should Not Apply")],
        items=[_item(item_name="Existing", active_status="active")],
    )
    key = ("rakuten", "shop:gift-1")
    snapshot = dict(repos.items[key])
    job = ItemApplyJob(repositories=repos)

    result = job.run(job_run_id="run-unavail")

    assert result.status == "succeeded"
    assert result.planned_diff_count == 0
    assert result.item_unavailable_skip_count == 1
    assert result.item_upsert_count == 0
    assert result.item_unchanged_touch_count == 0
    assert repos.items[key] == snapshot
    assert db.write_calls == []


def test_empty_image_set_sync_deletes_existing() -> None:
    repos, _ = _repos(
        diffs=[_diff(diff_status="updated", old_hash=_HASH_A, new_hash=_HASH_B)],
        staging=[_staging(normalized_hash=_HASH_B)],
        images=[],
        items=[_item(normalized_hash=_HASH_A)],
    )
    item_id = "it_shop_gift-1"
    repos.item_images[item_id] = {
        "https://img.example/old.jpg": {
            "item_id": item_id,
            "image_url": "https://img.example/old.jpg",
            "is_primary": True,
        }
    }
    job = ItemApplyJob(repositories=repos)

    result = job.run(job_run_id="run-empty-img")

    assert result.status == "succeeded"
    assert result.item_image_sync_count == 1
    assert repos.item_images[item_id] == {}


def test_review_missing_skips_without_delete() -> None:
    repos, _ = _repos(
        diffs=[_diff(diff_status="updated", old_hash=_HASH_A, new_hash=_HASH_B)],
        staging=[
            _staging(
                normalized_hash=_HASH_B,
                review_average=None,
                review_count=None,
            )
        ],
        items=[_item(normalized_hash=_HASH_A)],
    )
    item_id = "it_shop_gift-1"
    repos.item_reviews[item_id] = {
        "item_id": item_id,
        "review_average": 3.0,
        "review_count": 5,
    }
    job = ItemApplyJob(repositories=repos)

    result = job.run(job_run_id="run-rev-skip")

    assert result.status == "succeeded"
    assert result.item_review_skip_count == 1
    assert result.item_review_upsert_count == 0
    assert repos.item_reviews[item_id]["review_average"] == 3.0


def test_selection_by_diff_batch_run_id_and_external_codes() -> None:
    repos, _ = _repos(
        diffs=[
            _diff(
                product_diff_result_id="pdr_keep",
                batch_run_id="diff-run-keep",
                staging_item_id="si_keep",
                external_item_code="shop:keep",
                diff_status="new",
            ),
            _diff(
                product_diff_result_id="pdr_other_run",
                batch_run_id="diff-run-other",
                staging_item_id="si_other",
                external_item_code="shop:other",
                diff_status="new",
            ),
            _diff(
                product_diff_result_id="pdr_skip_code",
                batch_run_id="diff-run-keep",
                staging_item_id="si_skip",
                external_item_code="shop:skip",
                diff_status="new",
            ),
        ],
        staging=[
            _staging(staging_item_id="si_keep", external_item_code="shop:keep"),
            _staging(staging_item_id="si_other", external_item_code="shop:other"),
            _staging(staging_item_id="si_skip", external_item_code="shop:skip"),
        ],
    )
    job = ItemApplyJob(repositories=repos)

    result = job.run(
        job_run_id="run-filter",
        diff_batch_run_id="diff-run-keep",
        external_item_codes=["shop:keep"],
    )

    assert result.status == "succeeded"
    assert result.planned_diff_count == 1
    assert result.succeeded_external_codes == ["shop:keep"]
    assert ("rakuten", "shop:keep") in repos.items
    assert ("rakuten", "shop:other") not in repos.items
    assert ("rakuten", "shop:skip") not in repos.items


def test_hash_is_copied_not_recalculated() -> None:
    repos, _ = _repos(
        diffs=[_diff(diff_status="new")],
        staging=[_staging(normalized_hash=_HASH_B)],
    )
    job = ItemApplyJob(repositories=repos)

    result = job.run(job_run_id="run-hash")

    assert result.status == "succeeded"
    assert repos.items[("rakuten", "shop:gift-1")]["normalized_hash"] == _HASH_B
    assert result.hash_recalculate_calls == []
    assert repos.hash_recalculate_calls == []


def test_fixture_and_logs_have_no_secret_like_values() -> None:
    repos, _ = _repos()
    job = ItemApplyJob(repositories=repos)
    result = job.run(job_run_id="run-sec")

    blob = str(result) + str(repos.error_logs) + str(repos.phase_logs)
    assert _SECRET_PATTERN.search(blob) is None


def test_review_upsert_idempotent_unique_item_id_only() -> None:
    """§16 No.8: レビュー冪等。UNIQUE は item_id のみ（source 列なし）。再 Upsert で 1 行。"""

    repos, _ = _repos(
        diffs=[_diff(diff_status="updated", old_hash=_HASH_A, new_hash=_HASH_B)],
        staging=[
            _staging(
                normalized_hash=_HASH_B,
                review_average=4.5,
                review_count=20,
            )
        ],
        items=[_item(normalized_hash=_HASH_A)],
    )
    item_id = "it_shop_gift-1"
    repos.item_reviews[item_id] = {
        "item_id": item_id,
        "review_average": 3.0,
        "review_count": 5,
    }
    job = ItemApplyJob(repositories=repos)

    first = job.run(job_run_id="run-rev-idem-1")
    assert first.status == "succeeded"
    assert first.item_review_upsert_count == 1
    assert list(repos.item_reviews.keys()) == [item_id]
    assert "source" not in repos.item_reviews[item_id]
    assert repos.item_reviews[item_id]["review_average"] == 4.5
    assert repos.item_reviews[item_id]["review_count"] == 20

    # 同じ item_id へ再 Upsert（updated 再実行相当）
    repos.seed_diffs = [
        _diff(
            product_diff_result_id="pdr_2",
            diff_status="updated",
            old_hash=_HASH_B,
            new_hash=_HASH_B,
        )
    ]
    repos.product_diff_results = {
        "pdr_2": {
            "product_diff_result_id": "pdr_2",
            "batch_run_id": "diff-run-1",
            "staging_item_id": "si_1",
            "external_item_code": "shop:gift-1",
            "diff_status": "updated",
            "old_hash": _HASH_B,
            "new_hash": _HASH_B,
        }
    }
    repos.staging_items["si_1"]["review_average"] = 4.8
    repos.staging_items["si_1"]["review_count"] = 30
    repos.staging_items["si_1"]["normalized_hash"] = _HASH_B

    second = job.run(job_run_id="run-rev-idem-2")
    assert second.status == "succeeded"
    assert second.item_review_upsert_count == 1
    assert list(repos.item_reviews.keys()) == [item_id]
    assert len(repos.item_reviews) == 1
    assert "source" not in repos.item_reviews[item_id]
    assert repos.item_reviews[item_id]["review_average"] == 4.8
    assert repos.item_reviews[item_id]["review_count"] == 30


def test_idempotent_rerun_converges_item_image_review() -> None:
    """§16 No.9: 同一キー再実行で item / image / review が収束する。"""

    images = [
        StagingImageSeed(
            staging_item_id="si_1",
            image_url="https://img.example/a.jpg",
            display_order=0,
            is_primary_candidate=True,
        ),
        StagingImageSeed(
            staging_item_id="si_1",
            image_url="https://img.example/b.jpg",
            display_order=1,
            is_primary_candidate=False,
        ),
    ]
    repos, _ = _repos(images=images)
    job = ItemApplyJob(repositories=repos)

    first = job.run(job_run_id="run-idem-1")
    assert first.status == "succeeded"
    key = ("rakuten", "shop:gift-1")
    item_id = str(repos.items[key]["item_id"])
    snapshot_item = dict(repos.items[key])
    snapshot_images = {url: dict(row) for url, row in repos.item_images[item_id].items()}
    snapshot_review = dict(repos.item_reviews[item_id])

    second = job.run(job_run_id="run-idem-2")
    assert second.status == "succeeded"
    assert second.item_upsert_count == 1
    assert second.item_image_sync_count == 1
    assert second.item_review_upsert_count == 1

    assert str(repos.items[key]["item_id"]) == item_id
    assert repos.items[key]["item_name"] == snapshot_item["item_name"]
    assert repos.items[key]["normalized_hash"] == snapshot_item["normalized_hash"]
    assert repos.items[key]["price"] == snapshot_item["price"]
    assert set(repos.item_images[item_id].keys()) == set(snapshot_images.keys())
    for url, row in snapshot_images.items():
        assert repos.item_images[item_id][url]["image_url"] == row["image_url"]
        assert repos.item_images[item_id][url]["is_primary"] == row["is_primary"]
    assert len(repos.item_reviews) == 1
    assert repos.item_reviews[item_id]["review_average"] == snapshot_review["review_average"]
    assert repos.item_reviews[item_id]["review_count"] == snapshot_review["review_count"]


def test_partial_success_one_row_fails_grs_bat_002() -> None:
    """§16 No.10: 一部失敗で partially_succeeded + GRS-BAT-002。"""

    class _FailOneRepos(ItemApplyRepositories):
        def load_staging(self, *, staging_item_id: str):  # type: ignore[override]
            seed = super().load_staging(staging_item_id=staging_item_id)
            if seed.external_item_code != "shop:bad":
                return seed
            # 選定時は valid、process 中に hash NULL を返して当該行のみ失敗
            return StagingItemSeed(
                staging_item_id=seed.staging_item_id,
                source=seed.source,
                external_item_code=seed.external_item_code,
                normalized_hash=None,
                item_name=seed.item_name,
                price=seed.price,
                item_url=seed.item_url,
                review_average=seed.review_average,
                review_count=seed.review_count,
            )

    repos = _FailOneRepos(
        db_writer=ScaffoldDbWriter(),
        seed_diffs=[
            _diff(
                product_diff_result_id="pdr_ok",
                staging_item_id="si_ok",
                external_item_code="shop:ok",
                diff_status="new",
            ),
            _diff(
                product_diff_result_id="pdr_bad",
                staging_item_id="si_bad",
                external_item_code="shop:bad",
                diff_status="new",
            ),
        ],
        seed_staging=[
            _staging(staging_item_id="si_ok", external_item_code="shop:ok"),
            _staging(staging_item_id="si_bad", external_item_code="shop:bad"),
        ],
        seed_images=[],
        seed_items=[],
    )
    result = ItemApplyJob(repositories=repos).run(job_run_id="run-partial")

    assert result.status == "partially_succeeded"
    assert "GRS-BAT-002" in result.error_codes
    assert "GRS-BAT-005" in result.error_codes
    assert "shop:ok" in result.succeeded_external_codes
    assert "shop:bad" in result.failed_external_codes
    assert ("rakuten", "shop:ok") in repos.items
    assert ("rakuten", "shop:bad") not in repos.items
    assert any(e["code"] == "GRS-BAT-005" for e in repos.error_logs)


def test_concurrent_start_rejected_grs_bat_003() -> None:
    """§16 No.11: JobRunTracker の unpaired running → GRS-BAT-003。"""

    tracker = ScaffoldJobRunTracker()
    tracker.start(batch_id=BATCH_ID, job_run_id="already-running")
    repos, _ = _repos()
    job = ItemApplyJob(repositories=repos, job_run_tracker=tracker)

    result = job.run(job_run_id="run-concurrent")

    assert result.status == "failed"
    assert "GRS-BAT-003" in result.error_codes
    assert repos.items == {}
    assert any(e["code"] == "GRS-BAT-003" for e in repos.error_logs)


def test_boundary_tables_not_written() -> None:
    """§16 No.12: unit 代替。境界テーブルへ write しない（counters / write_calls）。"""

    images = [
        StagingImageSeed(
            staging_item_id="si_1",
            image_url="https://img.example/a.jpg",
            is_primary_candidate=True,
        )
    ]
    repos, db = _repos(images=images)
    result = ItemApplyJob(repositories=repos).run(job_run_id="run-boundary")

    assert result.status == "succeeded"
    written_tables = {c["table"] for c in db.write_calls}
    assert written_tables.isdisjoint(_FORBIDDEN_BOUNDARY_TABLES)
    assert "product_diff_result" not in written_tables
    assert "item_popularity_signal" not in written_tables
    assert "item_generation_queue" not in written_tables
    assert result.product_diff_write_count == 0
    assert repos.product_diff_write_count == 0


def test_image_sync_replaces_removed_urls() -> None:
    """任意強化: 画像同期で消えた URL を DELETE（空集合以外の置換）。"""

    repos, _ = _repos(
        diffs=[_diff(diff_status="updated", old_hash=_HASH_A, new_hash=_HASH_B)],
        staging=[_staging(normalized_hash=_HASH_B)],
        images=[
            StagingImageSeed(
                staging_item_id="si_1",
                image_url="https://img.example/keep.jpg",
                display_order=0,
                is_primary_candidate=True,
            ),
            StagingImageSeed(
                staging_item_id="si_1",
                image_url="https://img.example/new.jpg",
                display_order=1,
                is_primary_candidate=False,
            ),
        ],
        items=[_item(normalized_hash=_HASH_A)],
    )
    item_id = "it_shop_gift-1"
    repos.item_images[item_id] = {
        "https://img.example/old.jpg": {
            "item_id": item_id,
            "image_url": "https://img.example/old.jpg",
            "is_primary": True,
        },
        "https://img.example/keep.jpg": {
            "item_id": item_id,
            "image_url": "https://img.example/keep.jpg",
            "is_primary": False,
        },
    }
    result = ItemApplyJob(repositories=repos).run(job_run_id="run-img-replace")

    assert result.status == "succeeded"
    assert result.item_image_sync_count == 1
    synced = repos.item_images[item_id]
    assert set(synced.keys()) == {
        "https://img.example/keep.jpg",
        "https://img.example/new.jpg",
    }
    assert "https://img.example/old.jpg" not in synced


def test_image_unique_key_is_item_id_and_image_url() -> None:
    """任意強化: 画像 UNIQUE は (item_id, image_url)。同一 URL は 1 行に収束。"""

    repos, _ = _repos(
        images=[
            StagingImageSeed(
                staging_item_id="si_1",
                image_url="https://img.example/dup.jpg",
                display_order=0,
                is_primary_candidate=True,
            ),
            StagingImageSeed(
                staging_item_id="si_1",
                image_url="https://img.example/dup.jpg",
                display_order=1,
                is_primary_candidate=False,
            ),
        ]
    )
    result = ItemApplyJob(repositories=repos).run(job_run_id="run-img-unique")

    assert result.status == "succeeded"
    item_id = str(repos.items[("rakuten", "shop:gift-1")]["item_id"])
    synced = repos.item_images[item_id]
    assert list(synced.keys()) == ["https://img.example/dup.jpg"]
    assert synced["https://img.example/dup.jpg"]["item_id"] == item_id
    assert synced["https://img.example/dup.jpg"]["image_url"] == "https://img.example/dup.jpg"
