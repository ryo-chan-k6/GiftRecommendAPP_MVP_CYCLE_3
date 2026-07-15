"""Unit tests for BATCH-005 Raw取込・Staging変換（最小: 正常系 / hash / 冪等 / Item非更新）."""

from __future__ import annotations

import json

from batch.application.raw_staging import (
    BATCH_ID,
    RAW_STAGING_PHASES,
    RawMetadataSeed,
    RawStagingJob,
    RawStagingRepositories,
    build_normalized_payload,
    compute_normalized_hash,
    content_hash_for_bytes,
)
from batch.infrastructure.db import ScaffoldDbWriter
from batch.infrastructure.object_storage import ObjectRef, ScaffoldObjectStorageClient

_FORBIDDEN_TABLES = frozenset(
    {
        "item",
        "product_diff_result",
        "item_active_status",
        "external_genre",
    }
)


def _item_search_payload(*, code: str = "shop:gift-1") -> dict[str, object]:
    return {
        "Items": [
            {
                "Item": {
                    "itemCode": code,
                    "itemName": "Gift A",
                    "itemCaption": "Caption",
                    "catchcopy": "Catch",
                    "itemPrice": 2500,
                    "itemUrl": f"https://item.example/{code}",
                    "genreId": 101240,
                    "shopCode": "shop",
                    "availability": 1,
                    "reviewAverage": 4.2,
                    "reviewCount": 8,
                    "attributeIds": ["a1"],
                    "mediumImageUrls": [{"imageUrl": "https://img.example/m1.jpg"}],
                    "smallImageUrls": [{"imageUrl": "https://img.example/s1.jpg"}],
                }
            }
        ]
    }


def _seed_repos(
    *,
    payloads: dict[str, dict[str, object]] | None = None,
    import_status: str = "raw_saved",
) -> tuple[RawStagingRepositories, ScaffoldObjectStorageClient, ScaffoldDbWriter]:
    storage = ScaffoldObjectStorageClient()
    db = ScaffoldDbWriter()
    seeds: list[RawMetadataSeed] = []
    payload_map = payloads or {"rm_1": _item_search_payload()}

    for raw_id, payload in payload_map.items():
        key = f"raw/rakuten/item_search/{raw_id}.json"
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        storage.put_object(
            ObjectRef(bucket="test-raw", key=key),
            body=body,
            content_type="application/json",
        )
        seeds.append(
            RawMetadataSeed(
                raw_metadata_id=raw_id,
                object_key=key,
                content_hash=content_hash_for_bytes(body),
                source="rakuten",
                source_api="item_search",
                import_status=import_status,
            )
        )

    storage.put_calls.clear()
    repos = RawStagingRepositories(
        object_storage=storage,
        db_writer=db,
        bucket="test-raw",
        seed_raws=seeds,
    )
    return repos, storage, db


def test_happy_path_item_search_staging_upsert_and_staged_status() -> None:
    repos, storage, db = _seed_repos()
    job = RawStagingJob(repositories=repos)

    result = job.run(job_run_id="job-happy", max_raw=10)

    assert result.batch_id == BATCH_ID
    assert result.status == "succeeded"
    assert result.succeeded_raw_ids == ["rm_1"]
    assert result.staging_item_upsert_count == 1
    assert result.staging_item_image_upsert_count == 2
    assert set(RAW_STAGING_PHASES).issubset(set(result.completed_phases))

    item = repos.staging_items[("rm_1", "shop:gift-1")]
    assert item["item_name"] == "Gift A"
    assert item["price"] == 2500
    assert item["external_genre_id"] == 101240
    assert item["diff_status"] is None
    assert item["normalized_hash"]
    assert len(str(item["normalized_hash"])) == 64

    meta = repos.raw_metadata["rm_1"]
    assert meta["import_status"] == "staged"
    assert meta["staged_at"] is not None

    assert result.written_item_rows == []
    assert result.written_product_diff_rows == []
    assert result.written_active_status_rows == []
    assert result.written_external_genre_rows == []
    assert result.object_storage_put_count == 0
    assert len(storage.put_calls) == 0
    assert len(storage.get_calls) == 1

    written_tables = {call["table"] for call in db.write_calls}
    assert written_tables.isdisjoint(_FORBIDDEN_TABLES)
    assert "staging_item" in written_tables
    assert "staging_item_image" in written_tables
    assert "raw_product_metadata" in written_tables


def test_normalized_hash_is_stable() -> None:
    item = {
        "itemCode": "shop:x",
        "itemName": "X",
        "catchcopy": None,
        "itemCaption": "c",
        "itemPrice": 100,
        "itemUrl": "https://example/x",
        "genreId": 1,
        "shopCode": "shop",
        "availability": 1,
        "mediumImageUrls": [{"imageUrl": "https://img/m.jpg"}],
        "smallImageUrls": [],
        "reviewAverage": 3.0,
        "reviewCount": 1,
        "attributeIds": ["z", "a"],
    }
    payload_a = build_normalized_payload(item)
    payload_b = build_normalized_payload(dict(item))
    assert payload_a == payload_b
    assert compute_normalized_hash(payload_a) == compute_normalized_hash(payload_b)

    repos, _, _ = _seed_repos(payloads={"rm_hash": _item_search_payload(code="shop:hash")})
    job = RawStagingJob(repositories=repos)
    first = job.run(job_run_id="job-hash-1", max_raw=1, force=True)
    hash1 = repos.staging_items[("rm_hash", "shop:hash")]["normalized_hash"]

    # Reset status to re-stage with force (same Raw body)
    repos.raw_metadata["rm_hash"]["import_status"] = "raw_saved"
    second = job.run(job_run_id="job-hash-2", max_raw=1, force=True)
    hash2 = repos.staging_items[("rm_hash", "shop:hash")]["normalized_hash"]

    assert first.status == "succeeded"
    assert second.status == "succeeded"
    assert hash1 == hash2


def test_item_tables_not_written() -> None:
    repos, _, db = _seed_repos()
    job = RawStagingJob(repositories=repos)
    result = job.run(job_run_id="job-boundary", max_raw=5)

    assert result.status == "succeeded"
    assert result.written_item_rows == []
    assert result.written_product_diff_rows == []
    assert result.written_active_status_rows == []
    assert result.written_external_genre_rows == []
    for call in db.write_calls:
        assert call["table"] not in _FORBIDDEN_TABLES


def test_idempotent_rerun_skips_staged_then_force_upserts() -> None:
    repos, storage, _ = _seed_repos()
    job = RawStagingJob(repositories=repos)

    first = job.run(job_run_id="job-idem-1", max_raw=10)
    assert first.status == "succeeded"
    assert repos.raw_metadata["rm_1"]["import_status"] == "staged"
    staging_id = repos.staging_items[("rm_1", "shop:gift-1")]["staging_item_id"]
    hash1 = repos.staging_items[("rm_1", "shop:gift-1")]["normalized_hash"]
    get_count_after_first = len(storage.get_calls)

    # Default re-run: staged is skipped → noop success
    second = job.run(job_run_id="job-idem-2", max_raw=10)
    assert second.status == "succeeded"
    assert second.planned_raw_count == 0
    assert second.staging_item_upsert_count == 0
    assert len(storage.get_calls) == get_count_after_first  # no additional GET

    # Force re-stage: upsert same key, hash stable, status remains staged
    third = job.run(job_run_id="job-idem-3", max_raw=10, force=True)
    assert third.status == "succeeded"
    assert third.staging_item_upsert_count == 1
    assert repos.staging_items[("rm_1", "shop:gift-1")]["staging_item_id"] == staging_id
    assert repos.staging_items[("rm_1", "shop:gift-1")]["normalized_hash"] == hash1
    assert repos.staging_items[("rm_1", "shop:gift-1")]["diff_status"] is None
    assert repos.raw_metadata["rm_1"]["import_status"] == "staged"


def test_content_hash_mismatch_does_not_write_staging() -> None:
    repos, _, db = _seed_repos()
    repos.raw_metadata["rm_1"]["content_hash"] = "0" * 64
    job = RawStagingJob(repositories=repos)

    result = job.run(job_run_id="job-hash-mismatch", max_raw=10)

    assert result.status == "failed"
    assert "GRS-RAW-005" in result.error_codes
    assert repos.staging_items == {}
    assert repos.raw_metadata["rm_1"]["import_status"] == "failed"
    tables = {call["table"] for call in db.write_calls}
    assert "staging_item" not in tables


def test_image_sync_delete_on_rerun() -> None:
    payload_with_two = _item_search_payload()
    repos, storage, _ = _seed_repos(payloads={"rm_img": payload_with_two})
    job = RawStagingJob(repositories=repos)
    first = job.run(job_run_id="job-img-1", max_raw=1)
    assert first.status == "succeeded"
    assert len(repos.staging_item_images) == 2

    # Replace Raw body: only medium image remains
    new_payload = _item_search_payload(code="shop:gift-1")
    item = new_payload["Items"][0]["Item"]  # type: ignore[index]
    assert isinstance(item, dict)
    item["smallImageUrls"] = []
    item["mediumImageUrls"] = [{"imageUrl": "https://img.example/m1.jpg"}]
    body = json.dumps(new_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    key = str(repos.raw_metadata["rm_img"]["object_key"])
    storage.put_object(
        ObjectRef(bucket="test-raw", key=key),
        body=body,
        content_type="application/json",
    )
    storage.put_calls.clear()
    repos.raw_metadata["rm_img"]["content_hash"] = content_hash_for_bytes(body)
    repos.raw_metadata["rm_img"]["import_status"] = "raw_saved"

    second = job.run(job_run_id="job-img-2", max_raw=1, force=True)
    assert second.status == "succeeded"
    urls = {k[2] for k in repos.staging_item_images}
    assert urls == {"https://img.example/m1.jpg"}
