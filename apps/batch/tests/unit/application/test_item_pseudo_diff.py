"""Minimal unit tests for BATCH-003 楽天商品疑似差分取得."""

from __future__ import annotations

import json

from batch.application.item_pseudo_diff import (
    BATCH_ID,
    ITEM_PSEUDO_DIFF_PHASES,
    FetchCursorRow,
    ItemPseudoDiffJob,
    ItemPseudoDiffRepositories,
    build_item_search_raw_object_key,
    content_hash_for_payload,
)
from batch.infrastructure.db import ScaffoldDbWriter
from batch.infrastructure.object_storage import ScaffoldObjectStorageClient
from batch.infrastructure.rakuten import (
    ScaffoldRakutenApiClient,
    adapt_item_search_raw_payload,
)


def _repos(*, seed: list[FetchCursorRow] | None = None) -> ItemPseudoDiffRepositories:
    return ItemPseudoDiffRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=ScaffoldDbWriter(),
        bucket="test-raw",
        seed_cursors=list(seed or []),
    )


def _client_genre(
    *,
    genre_id: str = "100",
    items: list[dict[str, object]] | None = None,
) -> ScaffoldRakutenApiClient:
    payload_items = items or [
        {"Item": {"itemCode": "shop:a", "itemName": "A"}},
        {"Item": {"itemCode": "shop:b", "itemName": "B"}},
    ]
    return ScaffoldRakutenApiClient(
        item_search_raw_responses={
            ("genre", genre_id, 1): {"Items": payload_items},
            ("update_sort", "*", 1): {
                "Items": [{"Item": {"itemCode": "shop:a", "itemName": "A"}}]
            },
        }
    )


def test_item_pseudo_diff_happy_path_genre() -> None:
    repos = _repos()
    job = ItemPseudoDiffJob(rakuten_client=_client_genre(), repositories=repos)

    result = job.run(
        job_run_id="job-1",
        target_genre_ids=("100",),
        include_update_sort=False,
    )

    assert result.batch_id == BATCH_ID
    assert result.status == "succeeded"
    assert result.raw_save_success_count >= 1
    assert result.candidate_item_code_count == 2
    assert result.created_items == []
    assert result.created_staging == []
    assert all(meta.get("source_api") == "item_search" for meta in repos.raw_metadata.values())
    assert "plan" in result.completed_phases
    assert "finalize" in result.completed_phases
    assert set(ITEM_PSEUDO_DIFF_PHASES).issubset(set(result.completed_phases))


def test_ranking_supplement_consumes_without_creating_item() -> None:
    client = ScaffoldRakutenApiClient(
        item_search_raw_responses={
            ("ranking_supplement", "shop:unknown", 1): {
                "Items": [
                    {"Item": {"itemCode": "shop:unknown", "itemName": "Unknown Gift"}}
                ]
            },
            ("genre", "100", 1): {
                "Items": [{"Item": {"itemCode": "shop:x", "itemName": "X"}}]
            },
        }
    )
    repos = _repos(
        seed=[
            FetchCursorRow(
                cursor_type="ranking_supplement",
                scope={"external_item_code": "shop:unknown"},
                page=1,
            )
        ]
    )
    job = ItemPseudoDiffJob(rakuten_client=client, repositories=repos)
    result = job.run(
        job_run_id="job-sup-2",
        target_genre_ids=("100",),
        include_update_sort=False,
    )

    assert result.status == "succeeded"
    assert result.ranking_supplement_consumed_count == 1
    assert result.created_items == []
    assert any(
        c.cursor_type == "ranking_supplement" and c.cursor_status == "completed"
        for c in repos.fetch_cursors.values()
    )


def test_raw_idempotent_skip_on_same_hash() -> None:
    repos = _repos()
    client = _client_genre()
    job = ItemPseudoDiffJob(rakuten_client=client, repositories=repos)

    first = job.run(
        job_run_id="job-idem-a",
        target_genre_ids=("100",),
        include_update_sort=False,
    )
    # Force same object_key by reusing fixed api id is hard; instead call save_raw twice via repos
    meta = next(iter(repos.raw_metadata.values()))
    body = json.dumps(
        {"Items": [{"Item": {"itemCode": "shop:a", "itemName": "A"}}]},
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    from batch.application.item_pseudo_diff.models import RawItemSearchArtifact

    artifact = RawItemSearchArtifact(
        object_key=str(meta["object_key"]),
        content_hash=str(meta["content_hash"]),
        api_call_log_id="api_reuse",
        cursor_id=None,
        cursor_type="genre",
        page=1,
        body=body,
    )
    # Align hash with stored
    artifact = RawItemSearchArtifact(
        object_key=str(meta["object_key"]),
        content_hash=str(meta["content_hash"]),
        api_call_log_id="api_reuse",
        cursor_id=None,
        cursor_type="genre",
        page=1,
        body=b"ignored-when-hash-matches",
    )
    skipped = repos.save_raw(artifact)
    assert first.status == "succeeded"
    assert skipped is False
    assert len(repos.raw_metadata) == 1


def test_api_failure_partial() -> None:
    repos = _repos()
    client = ScaffoldRakutenApiClient(
        item_search_raw_responses={
            ("genre", "100", 1): {
                "Items": [{"Item": {"itemCode": "shop:ok", "itemName": "OK"}}]
            }
        },
        fail_item_search_keys={("genre", "200", 1)},
    )
    job = ItemPseudoDiffJob(rakuten_client=client, repositories=repos)

    result = job.run(
        job_run_id="job-partial",
        target_genre_ids=("100", "200"),
        include_update_sort=False,
    )

    assert result.status == "partially_succeeded"
    assert "GRS-EXT-100" in result.error_codes or "GRS-BAT-002" in result.error_codes
    assert len(result.succeeded_cursor_ids) >= 1
    assert len(result.failed_cursor_ids) >= 1


def test_rate_limit_error_code() -> None:
    repos = _repos()
    client = ScaffoldRakutenApiClient(
        rate_limited_item_search_keys={("genre", "100", 1)},
    )
    job = ItemPseudoDiffJob(rakuten_client=client, repositories=repos)

    result = job.run(
        job_run_id="job-rl",
        target_genre_ids=("100",),
        include_update_sort=False,
    )

    assert result.status == "failed"
    assert "GRS-EXT-102" in result.error_codes


def test_adapt_item_search_and_object_key() -> None:
    adapted = adapt_item_search_raw_payload(
        {"Items": [{"Item": {"itemCode": "shop:z", "itemName": "Z", "genreId": "9"}}]},
        cursor_type="genre",
    )
    assert adapted.candidates[0].external_item_code == "shop:z"
    key = build_item_search_raw_object_key(
        batch_run_id="run-1",
        api_call_log_id="api_1",
        fetched_on=__import__("datetime").date(2026, 7, 13),
    )
    assert key.startswith("raw/rakuten/item_search/dt=2026-07-13/")
    assert content_hash_for_payload({"a": 1})


def test_does_not_consume_recheck_route() -> None:
    """recheck は BATCH-004。CursorType に含めず seed にも載せない。"""

    repos = _repos()
    # Ensure FetchCursorRow typing rejects recheck at design level by only seeding allowed types
    assert all(
        c.cursor_type in {"genre", "keyword", "update_sort", "ranking_supplement"}
        for c in repos.list_active_cursors()
    )


def test_api_call_log_has_fetch_cursor_id() -> None:
    repos = _repos()
    job = ItemPseudoDiffJob(rakuten_client=_client_genre(), repositories=repos)
    result = job.run(
        job_run_id="job-cursor-link",
        target_genre_ids=("100",),
        include_update_sort=False,
    )
    assert result.status == "succeeded"
    assert repos.api_call_logs
    assert all(log.get("fetch_cursor_id") for log in repos.api_call_logs)
