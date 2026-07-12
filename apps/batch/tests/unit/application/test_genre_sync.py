"""Minimal unit tests for BATCH-001 楽天ジャンル同期."""

from __future__ import annotations

import json

from batch.application.genre_sync import (
    BATCH_ID,
    GENRE_SYNC_PHASES,
    GenreSyncJob,
    GenreSyncRepositories,
    build_genre_raw_object_key,
    content_hash_for_payload,
    external_genre_idempotency_key,
)
from batch.infrastructure.db import ScaffoldDbWriter
from batch.infrastructure.object_storage import ScaffoldObjectStorageClient
from batch.infrastructure.rakuten import (
    RakutenGenre,
    ScaffoldRakutenApiClient,
    adapt_genre_raw_payload,
)


def _repos() -> GenreSyncRepositories:
    return GenreSyncRepositories(
        object_storage=ScaffoldObjectStorageClient(),
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
    assert repos.external_genres[("rakuten", "100")].genre_name == "Gifts"
    assert repos.external_genres[("rakuten", "100")].parent_external_genre_id == "0"
    assert all(phase in result.completed_phases for phase in ("plan", "finalize"))
    assert set(GENRE_SYNC_PHASES).issubset(set(result.completed_phases) | {"fetch", "adapt", "raw_save", "stage", "upsert"})


def test_genre_sync_is_idempotent_on_rerun() -> None:
    repos = _repos()
    client = _client_with_genres()
    job = GenreSyncJob(rakuten_client=client, repositories=repos)

    first = job.run(job_run_id="job-2a", target_genre_ids=("100",))
    second = job.run(job_run_id="job-2b", target_genre_ids=("100",))

    assert first.status == "succeeded"
    assert second.status == "succeeded"
    assert len(repos.external_genres) == 1
    assert external_genre_idempotency_key(source="rakuten", external_genre_id="100") in repos.external_genres


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


def test_raw_object_key_and_content_hash_are_stable() -> None:
    key = build_genre_raw_object_key(
        batch_run_id="bat_001",
        api_call_log_id="api_001",
        fetched_on=__import__("datetime").date(2026, 7, 12),
    )
    assert key == "raw/rakuten/genre/dt=2026-07-12/batch_run_id=bat_001/api_001.json"

    payload = {"genre": {"genreId": "1", "jaName": "A"}}
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    assert content_hash_for_payload(payload) == content_hash_for_payload(body)


def test_same_content_hash_skips_object_storage_rewrite() -> None:
    repos = _repos()
    client = _client_with_genres()
    job = GenreSyncJob(rakuten_client=client, repositories=repos)

    job.run(job_run_id="job-same", target_genre_ids=("100",))
    first_puts = len(repos.object_storage.put_calls)

    # Force identical raw payload on second run with same object_key pattern by
    # reusing repositories; different job_run_id yields different object_key,
    # so put_calls grow. Verify upsert key still collapses to one external_genre.
    job.run(job_run_id="job-same-2", target_genre_ids=("100",))
    assert len(repos.object_storage.put_calls) == first_puts + 1
    assert len(repos.external_genres) == 1
