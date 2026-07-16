"""Unit tests for BATCH-007 Item反映（仕様書 §16 / §18.1 最小観点）."""

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
from batch.infrastructure.db import ScaffoldDbWriter

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
