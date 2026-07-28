"""Unit tests for BATCH-001 楽天ジャンル同期（仕様書 §16 No.1〜7）."""

from __future__ import annotations

import json
from datetime import date

import pytest

from batch.application.genre_sync import (
    BATCH_ID,
    GENRE_SYNC_PHASES,
    GenreSyncJob,
    GenreSyncRepositories,
    RawGenreArtifact,
    build_genre_raw_object_key,
    content_hash_for_payload,
    external_genre_idempotency_key,
)
from batch.infrastructure.db import ScaffoldDbWriter
from batch.infrastructure.object_storage import ScaffoldObjectStorageClient
from batch.infrastructure.rakuten import (
    RakutenGenre,
    RakutenGenreApiError,
    ScaffoldRakutenApiClient,
    adapt_genre_raw_payload,
)


def _repos(*, fail_on_put: bool = False) -> GenreSyncRepositories:
    return GenreSyncRepositories(
        object_storage=ScaffoldObjectStorageClient(fail_on_put=fail_on_put),
        db_writer=ScaffoldDbWriter(),
        bucket="test-raw",
    )


def _client_with_genres() -> ScaffoldRakutenApiClient:
    return ScaffoldRakutenApiClient(
        genres={
            "100": RakutenGenre(
                genre_id="100",
                genre_name="Gifts",
                parent_genre_id="0",
                genre_level=1,
                children=("101",),
            ),
            "101": RakutenGenre(
                genre_id="101",
                genre_name="Seasonal",
                parent_genre_id="100",
                genre_level=2,
            ),
        }
    )


# --- §16 No.1 正常系 ---


def test_genre_sync_happy_path_upserts_external_genre() -> None:
    repos = _repos()
    job = GenreSyncJob(rakuten_client=_client_with_genres(), repositories=repos)

    result = job.run(job_run_id="job-1", target_genre_ids=("100", "101"))

    assert result.batch_id == BATCH_ID
    assert result.status == "succeeded"
    assert set(result.succeeded_genre_ids) == {"100", "101"}
    assert result.failed_genre_ids == []
    assert result.upserted_external_genre_count == 2
    assert ("rakuten", "100") in repos.external_genres
    assert ("rakuten", "100") in repos.staging_genres
    assert repos.external_genres[("rakuten", "100")].genre_name == "Gifts"
    assert repos.external_genres[("rakuten", "100")].parent_external_genre_id == "0"
    assert len(repos.object_storage.put_calls) == 2
    assert all(meta["import_status"] == "staged" for meta in repos.raw_metadata.values())
    assert result.completed_phases == list(GENRE_SYNC_PHASES)
    succeeded_api = [log for log in repos.api_call_logs if log["status"] == "succeeded"]
    assert len(succeeded_api) == 2
    assert {log["genre_id"] for log in succeeded_api} == {"100", "101"}
    from uuid import UUID

    for log in succeeded_api:
        UUID(str(log["api_call_log_id"]))  # job は常時 UUID（DDL PK / Object key）


def test_genre_sync_default_plan_uses_root_genre() -> None:
    client = ScaffoldRakutenApiClient(
        genres={"0": RakutenGenre(genre_id="0", genre_name="Root", genre_level=0)}
    )
    repos = _repos()
    job = GenreSyncJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-default")

    assert result.status == "succeeded"
    assert result.planned_genre_ids == ("0",)
    assert ("rakuten", "0") in repos.external_genres


# --- §16 No.2 階層展開 ---


def test_adapt_genre_raw_payload_maps_ja_name_and_children() -> None:
    payload = {
        "genre": {"genreId": "200", "jaName": "Flowers", "level": 1},
        "ancestors": [{"genreId": "0"}],
        "children": [{"genreId": "201"}, {"genreId": "202"}],
    }

    genre = adapt_genre_raw_payload(payload, requested_genre_id="200")

    assert genre.genre_id == "200"
    assert genre.genre_name == "Flowers"
    assert genre.parent_genre_id == "0"
    assert genre.genre_level == 1
    assert genre.children == ("201", "202")


def test_adapt_genre_raw_payload_rejects_legacy_current_key() -> None:
    payload = {
        "current": {"genreId": "200", "jaName": "Flowers", "level": 1},
        "children": [],
    }

    with pytest.raises(RakutenGenreApiError) as exc_info:
        adapt_genre_raw_payload(payload, requested_genre_id="200")

    assert exc_info.value.code == "GRS-EXT-103"
    assert "missing genre object" in exc_info.value.message


def test_adapt_prefers_explicit_parent_genre_id_over_ancestors() -> None:
    payload = {
        "genre": {
            "genreId": "300",
            "jaName": "Food",
            "level": 2,
            "parentGenreId": "100",
        },
        "ancestors": [{"genreId": "0"}, {"genreId": "100"}],
        "children": [],
    }

    genre = adapt_genre_raw_payload(payload, requested_genre_id="300")

    assert genre.parent_genre_id == "100"
    assert genre.children == ()


def test_adapt_invalid_payload_raises_ext_103() -> None:
    with pytest.raises(RakutenGenreApiError) as exc_info:
        adapt_genre_raw_payload({"genre": {"genreId": "x"}}, requested_genre_id="x")

    assert exc_info.value.code == "GRS-EXT-103"


def test_genre_sync_persists_parent_from_hierarchy() -> None:
    client = ScaffoldRakutenApiClient(
        raw_responses={
            "101": {
                "genre": {"genreId": "101", "jaName": "Seasonal", "level": 2},
                "ancestors": [{"genreId": "100"}],
                "children": [{"genreId": "102"}],
            }
        }
    )
    repos = _repos()
    job = GenreSyncJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-hier", target_genre_ids=("101",))

    assert result.status == "succeeded"
    row = repos.external_genres[("rakuten", "101")]
    assert row.parent_external_genre_id == "100"
    assert row.genre_level == 2


# --- §16 No.3 冪等性 ---


def test_genre_sync_is_idempotent_on_rerun() -> None:
    repos = _repos()
    client = _client_with_genres()
    job = GenreSyncJob(rakuten_client=client, repositories=repos)

    first = job.run(job_run_id="job-2a", target_genre_ids=("100",))
    second = job.run(job_run_id="job-2b", target_genre_ids=("100",))

    assert first.status == "succeeded"
    assert second.status == "succeeded"
    assert len(repos.external_genres) == 1
    assert (
        external_genre_idempotency_key(source="rakuten", external_genre_id="100")
        in repos.external_genres
    )


def test_raw_object_key_and_content_hash_are_stable() -> None:
    key = build_genre_raw_object_key(
        batch_run_id="bat_001",
        api_call_log_id="api_001",
        fetched_on=date(2026, 7, 12),
    )
    assert key == "raw/rakuten/genre/dt=2026-07-12/batch_run_id=bat_001/api_001.json"

    payload = {"genre": {"genreId": "1", "jaName": "A"}}
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    assert content_hash_for_payload(payload) == content_hash_for_payload(body)


def test_same_content_hash_skips_object_storage_rewrite() -> None:
    """§16 No.3 / 仕様書 §11: 同一 object_key + content_hash なら put を skip する。"""

    repos = _repos()
    object_key = "raw/rakuten/genre/dt=2026-07-12/batch_run_id=test/api_001.json"
    body = b'{"genre":{"genreId":"100","jaName":"Gifts"}}'
    content_hash = content_hash_for_payload(body)
    artifact = RawGenreArtifact(
        object_key=object_key,
        content_hash=content_hash,
        api_call_log_id="api_001",
        genre_id="100",
        body=body,
    )

    repos.save_raw(artifact)
    first_puts = len(repos.object_storage.put_calls)

    repos.save_raw(
        RawGenreArtifact(
            object_key=object_key,
            content_hash=content_hash,
            api_call_log_id="api_002",
            genre_id="100",
            body=body,
        )
    )

    assert len(repos.object_storage.put_calls) == first_puts
    assert repos.raw_metadata[object_key]["api_call_log_id"] == "api_002"
    repos.raw_metadata[object_key]["import_status"] = "staged"
    repos.save_raw(
        RawGenreArtifact(
            object_key=object_key,
            content_hash=content_hash,
            api_call_log_id="api_003",
            genre_id="100",
            body=body,
        )
    )
    assert repos.raw_metadata[object_key]["import_status"] == "staged"
    assert repos.raw_metadata[object_key]["api_call_log_id"] == "api_003"


# --- §16 No.4 Rate Limit ---


def test_genre_sync_rate_limit_records_ext_102() -> None:
    # §16 No.4: MVP unit では scaffold が即 GRS-EXT-102 を返す。
    # 待機・再試行ループ本体は integration / 本番 Rate Limiter 側で検証する。
    client = _client_with_genres()
    client.rate_limited_genre_ids.add("101")
    repos = _repos()
    job = GenreSyncJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-rl", target_genre_ids=("100", "101"))

    assert result.status == "partially_succeeded"
    assert result.succeeded_genre_ids == ["100"]
    assert result.failed_genre_ids == ["101"]
    assert "GRS-EXT-102" in result.error_codes
    assert any(e["code"] == "GRS-EXT-102" for e in repos.error_logs)
    failed_api = [log for log in repos.api_call_logs if log["genre_id"] == "101"]
    assert failed_api and failed_api[0]["status"] == "failed"
    assert failed_api[0]["error_code"] == "GRS-EXT-102"


# --- §16 No.5 API失敗 ---


def test_genre_sync_partial_failure_marks_partially_succeeded() -> None:
    client = _client_with_genres()
    client.fail_genre_ids.add("101")
    repos = _repos()
    job = GenreSyncJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-3", target_genre_ids=("100", "101"))

    assert result.status == "partially_succeeded"
    assert result.succeeded_genre_ids == ["100"]
    assert result.failed_genre_ids == ["101"]
    assert "GRS-EXT-100" in result.error_codes
    assert "GRS-BAT-002" in result.error_codes
    assert ("rakuten", "100") in repos.external_genres
    assert ("rakuten", "101") not in repos.external_genres
    failed_api = [log for log in repos.api_call_logs if log["genre_id"] == "101"]
    assert failed_api and failed_api[0]["status"] == "failed"
    assert failed_api[0]["error_code"] == "GRS-EXT-100"
    assert any(e["code"] == "GRS-EXT-100" for e in repos.error_logs)


def test_genre_sync_all_failures_marks_failed() -> None:
    client = _client_with_genres()
    client.fail_genre_ids.update({"100", "101"})
    repos = _repos()
    job = GenreSyncJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-all-fail", target_genre_ids=("100", "101"))

    assert result.status == "failed"
    assert result.succeeded_genre_ids == []
    assert set(result.failed_genre_ids) == {"100", "101"}
    assert "GRS-EXT-100" in result.error_codes
    assert "GRS-BAT-001" in result.error_codes
    failed_api = [log for log in repos.api_call_logs if log["status"] == "failed"]
    assert len(failed_api) == 2
    assert all(log["error_code"] == "GRS-EXT-100" for log in failed_api)
    assert any(e["code"] == "GRS-EXT-100" for e in repos.error_logs)


def test_genre_sync_invalid_payload_partial_failure() -> None:
    client = ScaffoldRakutenApiClient(
        raw_responses={
            "100": {
                "genre": {"genreId": "100", "jaName": "Gifts", "level": 1},
                "ancestors": [],
                "children": [],
            },
            "bad": {"not_genre": True},
        }
    )
    repos = _repos()
    job = GenreSyncJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-bad", target_genre_ids=("100", "bad"))

    assert result.status == "partially_succeeded"
    assert result.succeeded_genre_ids == ["100"]
    assert result.failed_genre_ids == ["bad"]
    assert "GRS-EXT-103" in result.error_codes
    bad_api = [log for log in repos.api_call_logs if log["genre_id"] == "bad"]
    assert bad_api and bad_api[-1]["status"] == "failed"
    assert bad_api[-1]["error_code"] == "GRS-EXT-103"


# --- §16 No.6 Raw失敗 ---


def test_genre_sync_raw_save_failure_records_raw_001() -> None:
    client = _client_with_genres()
    repos = _repos(fail_on_put=True)
    job = GenreSyncJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-raw", target_genre_ids=("100",))

    assert result.status == "failed"
    assert result.failed_genre_ids == ["100"]
    assert "GRS-RAW-001" in result.error_codes
    assert "GRS-BAT-001" in result.error_codes
    assert ("rakuten", "100") not in repos.external_genres
    assert any(e["code"] == "GRS-RAW-001" for e in repos.error_logs)


def test_genre_sync_raw_save_partial_failure() -> None:
    """§16 No.6: 同一 Run 内で先ジャンル成功・後ジャンル Raw 失敗を検証する。"""

    client = _client_with_genres()
    storage = ScaffoldObjectStorageClient(fail_after_n_puts=1)
    repos = GenreSyncRepositories(
        object_storage=storage,
        db_writer=ScaffoldDbWriter(),
        bucket="test-raw",
    )
    job = GenreSyncJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-raw-partial", target_genre_ids=("100", "101"))

    assert result.status == "partially_succeeded"
    assert result.succeeded_genre_ids == ["100"]
    assert result.failed_genre_ids == ["101"]
    assert "GRS-RAW-001" in result.error_codes
    assert "GRS-BAT-002" in result.error_codes
    assert ("rakuten", "100") in repos.external_genres
    assert ("rakuten", "101") not in repos.external_genres
    assert any(
        e["code"] == "GRS-RAW-001" and e.get("genre_id") == "101" for e in repos.error_logs
    )


# --- §16 No.7 secret非含有 ---


def test_api_call_and_error_logs_do_not_contain_secret_fields() -> None:
    client = _client_with_genres()
    client.fail_genre_ids.add("101")
    repos = _repos()
    job = GenreSyncJob(rakuten_client=client, repositories=repos)

    job.run(job_run_id="job-sec", target_genre_ids=("100", "101"))

    forbidden = (
        "Authorization",
        "accessKey",
        "access_key",
        "RAKUTEN_ACCESS_KEY",
        "object_storage_secret_key",
        "application_id",
        "Bearer ",
    )
    blob = json.dumps({"api": repos.api_call_logs, "err": repos.error_logs}, ensure_ascii=False)
    for token in forbidden:
        assert token not in blob


def test_batch_settings_repr_masks_access_keys() -> None:
    from batch.config._scaffold import scaffold_batch_settings

    settings = scaffold_batch_settings()
    text = repr(settings)
    assert "scaffold-rakuten-access-key" not in text
    assert "scaffold-object-storage-access-key" not in text
    assert "scaffold-openai-api-key" not in text
    assert "rakuten_access_key='***'" in text
    assert "object_storage_access_key='***'" in text
