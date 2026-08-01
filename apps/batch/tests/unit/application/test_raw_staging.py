"""Unit tests for BATCH-005 Raw取込・Staging変換（仕様書 §16 unit 観点）."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from batch.application.job_run import ScaffoldJobRunTracker
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
from batch.infrastructure.object_storage import ObjectRef, ObjectStorageError, ScaffoldObjectStorageClient

_FORBIDDEN_TABLES = frozenset(
    {
        "item",
        "product_diff_result",
        "item_active_status",
        "external_genre",
    }
)

_FAKE_DELETE_TABLE = "staging_item_image_delete"


def _writer_tables(db: ScaffoldDbWriter) -> set[str]:
    tables: set[str] = set()
    for calls in (db.write_calls, db.upsert_calls, db.update_calls, db.delete_calls):
        tables.update(str(call["table"]) for call in calls)
    return tables


def _upsert_tables(db: ScaffoldDbWriter) -> set[str]:
    return {str(call["table"]) for call in db.upsert_calls}


def _update_tables(db: ScaffoldDbWriter) -> set[str]:
    return {str(call["table"]) for call in db.update_calls}

# §16 No.2: staging_item に置かない列（物理定義外 / affiliate 系）
_FORBIDDEN_STAGING_ITEM_COLUMNS = frozenset(
    {
        "affiliate_url",
        "affiliateUrl",
        "shop_name",
        "shopName",
        "source_api",
        "sourceApi",
    }
)

# §16 No.13: fixture / logs に実token風が残らないこと
_SECRET_PATTERN = re.compile(
    r"(?i)(sk-[a-z0-9]{10,}|bearer\s+[a-z0-9\-._~+/]+=*|ghp_[a-z0-9]{20,}|"
    r"xox[baprs]-[a-z0-9-]+|supabase\.co/.{20,})"
)


@dataclass
class _FailingGetStorage:
    """GET 失敗注入用 scaffold（§16 No.6 GRS-RAW-004）。"""

    inner: ScaffoldObjectStorageClient
    fail_on_get: bool = True
    put_calls: list[dict[str, object]] = field(default_factory=list)
    get_calls: list[ObjectRef] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.put_calls = self.inner.put_calls
        self.get_calls = self.inner.get_calls

    def put_object(
        self,
        ref: ObjectRef,
        *,
        body: bytes,
        content_type: str,
    ) -> Any:
        return self.inner.put_object(ref, body=body, content_type=content_type)

    def get_object(self, ref: ObjectRef) -> Any:
        self.inner.get_calls.append(ref)
        if self.fail_on_get:
            raise ObjectStorageError(code="GRS-RAW-004", message="scaffold forced get failure")
        return self.inner.get_object(ref)


def _item_search_payload(
    *,
    code: str = "shop:gift-1",
    item_name: str = "Gift A",
    item_url: str | None = None,
    item_price: int = 2500,
) -> dict[str, object]:
    return {
        "Items": [
            {
                "Item": {
                    "itemCode": code,
                    "itemName": item_name,
                    "itemCaption": "Caption",
                    "catchcopy": "Catch",
                    "itemPrice": item_price,
                    "itemUrl": item_url if item_url is not None else f"https://item.example/{code}",
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
    source_api: str = "item_search",
    source_api_by_raw: dict[str, str] | None = None,
) -> tuple[RawStagingRepositories, ScaffoldObjectStorageClient, ScaffoldDbWriter]:
    storage = ScaffoldObjectStorageClient()
    db = ScaffoldDbWriter()
    seeds: list[RawMetadataSeed] = []
    payload_map = payloads or {"rm_1": _item_search_payload()}

    for raw_id, payload in payload_map.items():
        api = (source_api_by_raw or {}).get(raw_id, source_api)
        key = f"raw/rakuten/{api}/{raw_id}.json"
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
                source_api=api,
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

    written_tables = _writer_tables(db)
    assert written_tables.isdisjoint(_FORBIDDEN_TABLES)
    assert "staging_item" in _upsert_tables(db)
    assert "staging_item_image" in _upsert_tables(db)
    assert "raw_product_metadata" in _update_tables(db)
    assert _FAKE_DELETE_TABLE not in written_tables

    staging_upsert = next(c for c in db.upsert_calls if c["table"] == "staging_item")
    assert staging_upsert["conflict_columns"] == ("raw_metadata_id", "external_item_code")
    assert "staging_item_id" not in staging_upsert["rows"][0]
    assert "staging_item_id" not in (staging_upsert["update_columns"] or ())
    assert staging_upsert["rows"][0]["diff_status"] is None

    staged_update = next(c for c in db.update_calls if c["table"] == "raw_product_metadata")
    assert staged_update["set_values"]["import_status"] == "staged"
    assert "staged_at" in staged_update["set_values"]
    assert staged_update["equals"] == (("raw_metadata_id", "rm_1"),)


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
    for table in _writer_tables(db):
        assert table not in _FORBIDDEN_TABLES
    assert _FAKE_DELETE_TABLE not in _writer_tables(db)


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
    assert repos.raw_metadata["rm_1"]["error_message"] == "staging failed: GRS-RAW-005"
    tables = _writer_tables(db)
    assert "staging_item" not in tables
    failed_update = next(c for c in db.update_calls if c["table"] == "raw_product_metadata")
    assert failed_update["set_values"]["import_status"] == "failed"
    assert failed_update["set_values"]["error_code"] == "GRS-RAW-005"
    assert failed_update["set_values"]["error_message"] == "staging failed: GRS-RAW-005"


def test_image_sync_delete_on_rerun() -> None:
    payload_with_two = _item_search_payload()
    repos, storage, db = _seed_repos(payloads={"rm_img": payload_with_two})
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
    assert _FAKE_DELETE_TABLE not in _writer_tables(db)
    assert any(
        call["table"] == "staging_item_image"
        and call["equals"][-1] == ("image_url", "https://img.example/s1.jpg")
        for call in db.delete_calls
    )
    image_upsert = next(c for c in db.upsert_calls if c["table"] == "staging_item_image")
    assert image_upsert["conflict_columns"] == (
        "raw_metadata_id",
        "external_item_code",
        "image_url",
    )


def test_physical_column_mapping_excludes_affiliate_shop_name_source_api() -> None:
    """§16 No.2: price / external_genre_id あり。affiliate / shop_name / source_api 列なし。"""

    repos, _, _ = _seed_repos()
    job = RawStagingJob(repositories=repos)
    result = job.run(job_run_id="job-cols", max_raw=1)

    assert result.status == "succeeded"
    item = repos.staging_items[("rm_1", "shop:gift-1")]
    assert item["price"] == 2500
    assert item["external_genre_id"] == 101240
    assert "price" in item
    assert "external_genre_id" in item
    for col in _FORBIDDEN_STAGING_ITEM_COLUMNS:
        assert col not in item


def test_raw_object_missing_returns_grs_raw_003() -> None:
    """§16 No.6: Raw Object 不在 → GRS-RAW-003、Staging 非書込、metadata failed。"""

    repos, storage, db = _seed_repos()
    storage.objects.clear()
    job = RawStagingJob(repositories=repos)

    result = job.run(job_run_id="job-raw-003", max_raw=1)

    assert result.status == "failed"
    assert "GRS-RAW-003" in result.error_codes
    assert result.failed_raw_ids == ["rm_1"]
    assert repos.staging_items == {}
    assert repos.raw_metadata["rm_1"]["import_status"] == "failed"
    assert "staging_item" not in _writer_tables(db)
    assert any(
        c["set_values"].get("error_message") == "staging failed: GRS-RAW-003"
        for c in db.update_calls
        if c["table"] == "raw_product_metadata"
    )


def test_raw_get_failure_returns_grs_raw_004() -> None:
    """§16 No.6: Storage GET 失敗 → GRS-RAW-004（mock storage unit 代替）。"""

    repos, storage, db = _seed_repos()
    repos.object_storage = _FailingGetStorage(inner=storage)
    job = RawStagingJob(repositories=repos)

    result = job.run(job_run_id="job-raw-004", max_raw=1)

    assert result.status == "failed"
    assert "GRS-RAW-004" in result.error_codes
    assert result.failed_raw_ids == ["rm_1"]
    assert repos.staging_items == {}
    assert repos.raw_metadata["rm_1"]["import_status"] == "failed"
    assert "staging_item" not in _writer_tables(db)


def test_validation_missing_required_rejects_without_staging_write() -> None:
    """§16 No.7: 必須欠落で GRS-VAL-*、正本（staging_item）非更新。"""

    payload = _item_search_payload(item_name="")
    # empty itemUrl as well — transform keeps empty string → GRS-VAL-001
    item = payload["Items"][0]["Item"]  # type: ignore[index]
    assert isinstance(item, dict)
    item["itemUrl"] = ""
    repos, _, db = _seed_repos(payloads={"rm_val": payload})
    job = RawStagingJob(repositories=repos)

    result = job.run(job_run_id="job-val", max_raw=1)

    assert result.status == "failed"
    assert any(code.startswith("GRS-VAL-") for code in result.error_codes)
    assert result.validation_reject_count >= 1 or "GRS-VAL-001" in result.error_codes
    assert repos.staging_items == {}
    assert repos.raw_metadata["rm_val"]["import_status"] == "failed"
    assert "staging_item" not in _writer_tables(db)


def test_validation_failure_stderr_includes_object_key_and_payload_keys(
    capsys,
) -> None:
    """失敗時 stderr に object_key と payload keys（secret なし）を出す。"""

    payload = _item_search_payload()
    item = payload["Items"][0]["Item"]  # type: ignore[index]
    assert isinstance(item, dict)
    item["itemUrl"] = ""
    repos, _, _ = _seed_repos(payloads={"rm_diag": payload})
    job = RawStagingJob(repositories=repos)

    result = job.run(job_run_id="job-diag", max_raw=1)

    assert result.status == "failed"
    assert "GRS-VAL-001" in result.error_codes
    err = capsys.readouterr().err
    assert "raw_staging.raw_failed" in err
    assert "object_key=" in err
    assert "rm_diag" in err or "raw_metadata_id=rm_diag" in err
    assert "first_item_keys=" in err
    assert "itemUrl" in err


def test_ranking_and_genre_upsert_without_polluting_staging_item() -> None:
    """§16 No.8: ranking/genre は Staging 書込成功。staging_item / external_genre 非書込。"""

    ranking_payload = {
        "lastBuildDate": "2026-07-13T12:00:00+0900",
        "genreId": 100371,
        "period": "daily",
        "Items": [
            {"rank": 1, "itemCode": "shop:rank-1"},
            {"Item": {"rank": 2, "itemCode": "shop:rank-2"}},
        ],
    }
    genre_payload = {
        "genre": {
            "genreId": 0,
            "genreName": "root",
            "level": 0,
            "parentGenreId": None,
        },
        "children": [
            {
                "genreId": 100371,
                "jaName": "レディースファッション",
                "level": 1,
                "parentGenreId": 0,
            }
        ],
        "ancestors": [],
        "siblings": [],
    }
    repos, _, db = _seed_repos(
        payloads={
            "rm_rank": ranking_payload,
            "rm_genre": genre_payload,
        },
        source_api_by_raw={
            "rm_rank": "item_ranking",
            "rm_genre": "genre_search",
        },
    )
    job = RawStagingJob(repositories=repos)

    result = job.run(
        job_run_id="job-rank-genre",
        max_raw=10,
        source_api=("item_ranking", "genre_search"),
    )

    assert result.status == "succeeded"
    assert set(result.succeeded_raw_ids) == {"rm_rank", "rm_genre"}
    assert result.skipped_raw_ids == []
    assert result.staging_item_upsert_count == 0
    assert result.staging_ranking_signal_upsert_count == 2
    assert result.staging_genre_upsert_count == 2
    assert repos.staging_items == {}
    assert ("rm_rank", 1) in repos.staging_ranking
    assert ("rm_rank", 2) in repos.staging_ranking
    assert repos.staging_ranking[("rm_rank", 1)]["external_item_code"] == "shop:rank-1"
    assert repos.staging_ranking[("rm_rank", 1)]["external_genre_id"] == 100371
    assert ("rm_genre", 0) in repos.staging_genre
    assert ("rm_genre", 100371) in repos.staging_genre
    assert repos.staging_genre[("rm_genre", 0)]["is_leaf"] is False
    assert repos.staging_genre[("rm_genre", 100371)]["is_leaf"] is True
    assert repos.raw_metadata["rm_rank"]["import_status"] == "staged"
    assert repos.raw_metadata["rm_genre"]["import_status"] == "staged"
    assert result.written_external_genre_rows == []
    assert result.written_item_rows == []
    assert result.written_product_diff_rows == []

    written = _writer_tables(db)
    assert "staging_item" not in written
    assert "staging_item_image" not in written
    assert "staging_ranking_signal" in _upsert_tables(db)
    assert "staging_genre" in _upsert_tables(db)
    assert "raw_product_metadata" in _update_tables(db)
    assert written.isdisjoint(_FORBIDDEN_TABLES)

    ranking_upsert = next(c for c in db.upsert_calls if c["table"] == "staging_ranking_signal")
    assert ranking_upsert["conflict_columns"] == ("raw_metadata_id", "rank")
    assert "staging_ranking_signal_id" not in ranking_upsert["rows"][0]
    assert ranking_upsert["update_columns"] == (
        "external_item_code",
        "external_genre_id",
        "period",
        "last_build_date",
        "staged_at",
    )

    genre_upsert = next(c for c in db.upsert_calls if c["table"] == "staging_genre")
    assert genre_upsert["conflict_columns"] == ("raw_metadata_id", "external_genre_id")
    assert "staging_genre_id" not in genre_upsert["rows"][0]
    assert genre_upsert["update_columns"] == (
        "source",
        "genre_name",
        "parent_external_genre_id",
        "genre_level",
        "is_leaf",
        "staged_at",
    )

def test_failed_reset_to_raw_saved_then_restage() -> None:
    """§16 No.10: failed → raw_saved リセット後に再ステージ可（test-only metadata 更新）。"""

    repos, _, _ = _seed_repos()
    # Induce failure via content_hash mismatch
    repos.raw_metadata["rm_1"]["content_hash"] = "0" * 64
    job = RawStagingJob(repositories=repos)

    failed = job.run(job_run_id="job-reset-1", max_raw=1)
    assert failed.status == "failed"
    assert repos.raw_metadata["rm_1"]["import_status"] == "failed"
    assert repos.staging_items == {}

    # Production reset helper is out of UT scope; exercise eligibility via metadata reset
    key = str(repos.raw_metadata["rm_1"]["object_key"])
    stored = repos.object_storage.get_object(ObjectRef(bucket="test-raw", key=key))
    assert stored is not None
    repos.raw_metadata["rm_1"]["content_hash"] = content_hash_for_bytes(stored.body)
    repos.raw_metadata["rm_1"]["import_status"] = "raw_saved"
    repos.raw_metadata["rm_1"].pop("error_code", None)

    restaged = job.run(job_run_id="job-reset-2", max_raw=1)
    assert restaged.status == "succeeded"
    assert restaged.succeeded_raw_ids == ["rm_1"]
    assert ("rm_1", "shop:gift-1") in repos.staging_items
    assert repos.raw_metadata["rm_1"]["import_status"] == "staged"


def test_partial_success_one_raw_fails_grs_bat_002() -> None:
    """§16 No.11: 一部 Raw 失敗で partially_succeeded + GRS-BAT-002。"""

    repos, _, _ = _seed_repos(
        payloads={
            "rm_ok": _item_search_payload(code="shop:ok"),
            "rm_bad": _item_search_payload(code="shop:bad"),
        }
    )
    repos.raw_metadata["rm_bad"]["content_hash"] = "f" * 64
    job = RawStagingJob(repositories=repos)

    result = job.run(job_run_id="job-partial", max_raw=10)

    assert result.status == "partially_succeeded"
    assert "GRS-BAT-002" in result.error_codes
    assert "rm_ok" in result.succeeded_raw_ids
    assert "rm_bad" in result.failed_raw_ids
    assert ("rm_ok", "shop:ok") in repos.staging_items
    assert ("rm_bad", "shop:bad") not in repos.staging_items
    assert repos.raw_metadata["rm_ok"]["import_status"] == "staged"
    assert repos.raw_metadata["rm_bad"]["import_status"] == "failed"


def test_empty_items_item_search_raw_is_skipped_not_failed() -> None:
    """BATCH-003 catalog exhausted（空 Items）Raw は skip + succeeded（シナリオ停止しない）。"""

    empty_payload = {
        "Items": [],
        "carrier": 0,
        "count": 0,
        "first": 0,
        "hits": 30,
        "last": 0,
        "page": 1,
        "pageCount": 0,
    }
    repos, _, _ = _seed_repos(payloads={"rm_empty": empty_payload})
    job = RawStagingJob(repositories=repos)

    result = job.run(job_run_id="job-empty-items", max_raw=1)

    assert result.status == "succeeded"
    assert result.skipped_raw_ids == ["rm_empty"]
    assert result.failed_raw_ids == []
    assert result.succeeded_raw_ids == []
    assert "GRS-VAL-001" not in result.error_codes
    assert "GRS-BAT-001" not in result.error_codes
    assert repos.raw_metadata["rm_empty"]["import_status"] == "staged"


def test_concurrent_start_rejected_with_grs_bat_003() -> None:
    """§16 No.12: 同一 Batch 多重起動 → GRS-BAT-003。"""

    repos, _, _ = _seed_repos()
    tracker = ScaffoldJobRunTracker()
    # Leave an unpaired running record for BATCH-005
    tracker.start(batch_id=BATCH_ID, job_run_id="job-already-running")
    job = RawStagingJob(repositories=repos, job_run_tracker=tracker)

    result = job.run(job_run_id="job-double", max_raw=1)

    assert result.status == "failed"
    assert result.error_codes == ["GRS-BAT-003"]
    assert repos.staging_items == {}
    assert repos.raw_metadata["rm_1"]["import_status"] == "raw_saved"
    assert any(e["code"] == "GRS-BAT-003" for e in repos.error_logs)


def test_secret_non_containment_in_fixtures_and_error_logs() -> None:
    """§16 No.13: fixture / error_logs に実 token 風文字列がない。"""

    payload = _item_search_payload()
    blob = json.dumps(payload, ensure_ascii=False)
    assert _SECRET_PATTERN.search(blob) is None

    repos, _, _ = _seed_repos(payloads={"rm_sec": payload})
    repos.raw_metadata["rm_sec"]["content_hash"] = "0" * 64
    job = RawStagingJob(repositories=repos)
    result = job.run(job_run_id="job-secret-check", max_raw=1)
    assert result.status == "failed"

    for entry in repos.error_logs:
        text = json.dumps(entry, ensure_ascii=False, default=str)
        assert _SECRET_PATTERN.search(text) is None
    for code in result.error_codes:
        assert _SECRET_PATTERN.search(code) is None


def test_list_eligible_raws_uses_db_reader_when_injected() -> None:
    """Wave A: DbReader 注入時は seed ではなく SELECT 経路を使う。"""

    from batch.infrastructure.db import ScaffoldDbReader

    storage = ScaffoldObjectStorageClient()
    reader = ScaffoldDbReader()
    reader.seed(
        "raw_product_metadata",
        (
            {
                "raw_metadata_id": "rm_db_1",
                "object_key": "raw/rakuten/item_search/rm_db_1.json",
                "content_hash": "a" * 64,
                "source": "rakuten",
                "source_api": "item_search",
                "import_status": "raw_saved",
            },
            {
                "raw_metadata_id": "rm_db_skip",
                "object_key": "raw/rakuten/item_search/rm_db_skip.json",
                "content_hash": "b" * 64,
                "source": "rakuten",
                "source_api": "item_search",
                "import_status": "staged",
            },
        ),
    )
    repos = RawStagingRepositories(
        object_storage=storage,
        db_writer=ScaffoldDbWriter(),
        db_reader=reader,
        bucket="test-raw",
        seed_raws=[],
    )

    selected = repos.list_eligible_raws(max_raw=10)
    assert [s.raw_metadata_id for s in selected] == ["rm_db_1"]
    assert reader.fetch_calls
    assert reader.fetch_calls[0]["table"] == "raw_product_metadata"
    assert ("import_status", "raw_saved") in reader.fetch_calls[0]["equals"]


def test_list_eligible_raws_filters_by_bound_pipeline_batch_run_id() -> None:
    """他 Run の raw_saved 残骸を拾わず、object_key の batch_run_id で絞る。"""

    from batch.infrastructure.db import ScaffoldDbReader

    pipeline = "870575bf-d720-455a-a256-c74951400a50"
    other = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    reader = ScaffoldDbReader()
    reader.seed(
        "raw_product_metadata",
        (
            {
                "raw_metadata_id": "rm_old_bad",
                "object_key": (
                    f"raw/rakuten/item_search/dt=2026-07-28/"
                    f"batch_run_id={other}/old.json"
                ),
                "content_hash": "a" * 64,
                "source": "rakuten",
                "source_api": "item_search",
                "import_status": "raw_saved",
            },
            {
                "raw_metadata_id": "rm_new_good",
                "object_key": (
                    f"raw/rakuten/item_search/dt=2026-07-28/"
                    f"batch_run_id={pipeline}/new.json"
                ),
                "content_hash": "b" * 64,
                "source": "rakuten",
                "source_api": "item_search",
                "import_status": "raw_saved",
            },
        ),
    )
    repos = RawStagingRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=ScaffoldDbWriter(),
        db_reader=reader,
        bucket="test-raw",
    )
    repos.bind_run(batch_run_id=pipeline)

    selected = repos.list_eligible_raws(max_raw=1)
    assert [s.raw_metadata_id for s in selected] == ["rm_new_good"]


def test_list_eligible_raws_db_reader_force_and_explicit_ids() -> None:
    from batch.infrastructure.db import ScaffoldDbReader

    reader = ScaffoldDbReader()
    reader.seed(
        "raw_product_metadata",
        (
            {
                "raw_metadata_id": "rm_f1",
                "object_key": "k1",
                "content_hash": "c" * 64,
                "source": "rakuten",
                "source_api": "item_search",
                "import_status": "staged",
            },
        ),
    )
    repos = RawStagingRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=ScaffoldDbWriter(),
        db_reader=reader,
        bucket="test-raw",
    )

    forced = repos.list_eligible_raws(max_raw=5, force=True)
    assert [s.raw_metadata_id for s in forced] == ["rm_f1"]

    by_id = repos.list_eligible_raws(
        max_raw=5,
        raw_metadata_ids=("rm_f1",),
        force=True,
    )
    assert [s.raw_metadata_id for s in by_id] == ["rm_f1"]


def test_cli_non_demo_requires_database_url(monkeypatch: Any) -> None:
    from dataclasses import replace

    from batch.application.raw_staging import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(scaffold_batch_settings(), database_url=None),
    )
    code = cli.main(["--job-run-id", "no-db"])
    assert code == 2


def test_cli_non_demo_runs_job_with_live_reader(monkeypatch: Any) -> None:
    """DATABASE_URL ありなら exit 3 固定せず Job を起動する。"""

    from dataclasses import replace

    from batch.application.raw_staging import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings
    from batch.infrastructure.db import ScaffoldDbReader, ScaffoldDbWriter
    from batch.infrastructure.object_storage import ScaffoldObjectStorageClient

    reader = ScaffoldDbReader()
    reader.backend = "postgres"  # pretend live for is_live_db_reader

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(
            scaffold_batch_settings(),
            database_url="postgresql://localhost:5432/gift",
            object_storage_bucket="test-raw",
        ),
    )
    monkeypatch.setattr(cli, "create_db_writer", lambda _url: ScaffoldDbWriter())
    monkeypatch.setattr(
        cli,
        "resolve_job_db_reader",
        lambda **_kwargs: reader,
    )
    monkeypatch.setattr(
        cli,
        "create_object_storage_client",
        lambda *_args, **_kwargs: ScaffoldObjectStorageClient(),
    )
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

    code = cli.main(["--job-run-id", "wave-a", "--max-raw", "1"])
    # empty SELECT → plan failed (exit 1). Important: Job started (not config/exit-2/old exit-3).
    assert code == 1
    assert reader.fetch_calls


def test_cli_batch_run_id_fallback_to_job_run_id() -> None:
    from batch.application.raw_staging.__main__ import _resolve_business_run_id

    assert _resolve_business_run_id(job_run_id="leaf", batch_run_id="") == "leaf"
    assert (
        _resolve_business_run_id(job_run_id="leaf", batch_run_id="pipeline") == "pipeline"
    )
