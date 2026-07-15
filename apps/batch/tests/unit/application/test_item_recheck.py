"""Minimal unit tests for BATCH-004 楽天既存商品再確認."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from batch.application.item_recheck import (
    BATCH_ID,
    ITEM_RECHECK_PHASES,
    ItemRecheckJob,
    ItemRecheckRepositories,
    ItemSeed,
    build_item_search_raw_object_key,
    content_hash_for_payload,
    resolve_active_status_candidate,
)
from batch.application.item_recheck.models import RawItemSearchArtifact
from batch.infrastructure.db import ScaffoldDbWriter
from batch.infrastructure.object_storage import ScaffoldObjectStorageClient
from batch.infrastructure.rakuten import (
    ScaffoldRakutenApiClient,
    adapt_item_search_raw_payload,
)


def _repos(*, seeds: list[ItemSeed] | None = None) -> ItemRecheckRepositories:
    return ItemRecheckRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=ScaffoldDbWriter(),
        bucket="test-raw",
        seed_items=list(seeds or []),
    )


def _client_for(codes: dict[str, dict[str, object]]) -> ScaffoldRakutenApiClient:
    responses = {("recheck", code, 1): payload for code, payload in codes.items()}
    return ScaffoldRakutenApiClient(item_search_raw_responses=responses)


def test_happy_path_api_success_active() -> None:
    seeds = [
        ItemSeed(
            source="rakuten",
            external_item_code="shop:ok",
            item_id="item_ok",
            active_status="active",
        )
    ]
    client = _client_for(
        {
            "shop:ok": {
                "Items": [
                    {
                        "Item": {
                            "itemCode": "shop:ok",
                            "itemName": "OK Gift",
                            "availability": 1,
                        }
                    }
                ]
            }
        }
    )
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-happy", max_items=10)

    assert result.batch_id == BATCH_ID
    assert result.status == "succeeded"
    assert result.raw_save_success_count == 1
    assert result.candidate_upsert_count == 1
    assert result.created_items == []
    assert result.created_staging == []
    assert result.updated_item_rows == []

    key = ("job-happy", "rakuten", "shop:ok")
    cand = repos.candidates[key]
    assert cand["candidate_status"] == "detected"
    assert cand["detection_basis"] == "api_success"
    assert cand["reason_code"] == "available"
    assert cand["candidate_active_status"] == "active"
    assert cand["applied_at"] is None
    assert all(meta.get("source_api") == "item_search" for meta in repos.raw_metadata.values())
    # candidate must not be written into raw metadata
    assert all("candidate_active_status" not in meta for meta in repos.raw_metadata.values())


def test_empty_hit_candidate_unavailable_item_not_updated() -> None:
    seeds = [
        ItemSeed(
            source="rakuten",
            external_item_code="shop:gone",
            item_id="item_gone",
            active_status="active",
        )
    ]
    client = _client_for({"shop:gone": {"Items": []}})
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-empty", max_items=10)

    assert result.status == "succeeded"
    assert result.empty_hit_count == 1
    cand = repos.candidates[("job-empty", "rakuten", "shop:gone")]
    assert cand["detection_basis"] == "empty_hit"
    assert cand["reason_code"] == "empty_hit"
    assert cand["candidate_active_status"] == "unavailable"
    assert result.updated_item_rows == []
    assert result.created_items == []


def test_availability_zero_unavailable() -> None:
    seeds = [
        ItemSeed(
            source="rakuten",
            external_item_code="shop:zero",
            item_id="item_zero",
            active_status="active",
        )
    ]
    client = _client_for(
        {
            "shop:zero": {
                "Items": [
                    {
                        "Item": {
                            "itemCode": "shop:zero",
                            "itemName": "Zero",
                            "availability": 0,
                        }
                    }
                ]
            }
        }
    )
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-zero", max_items=10)

    assert result.status == "succeeded"
    assert result.availability_zero_count == 1
    cand = repos.candidates[("job-zero", "rakuten", "shop:zero")]
    assert cand["detection_basis"] == "availability"
    assert cand["reason_code"] == "availability_zero"
    assert cand["candidate_active_status"] == "unavailable"


def test_raw_idempotent_skip_on_same_hash() -> None:
    seeds = [
        ItemSeed(
            source="rakuten",
            external_item_code="shop:a",
            active_status="active",
        )
    ]
    payload = {
        "Items": [{"Item": {"itemCode": "shop:a", "itemName": "A", "availability": 1}}]
    }
    client = _client_for({"shop:a": payload})
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)

    first = job.run(job_run_id="job-idem", max_items=10)
    meta = next(iter(repos.raw_metadata.values()))
    artifact = RawItemSearchArtifact(
        object_key=str(meta["object_key"]),
        content_hash=str(meta["content_hash"]),
        api_call_log_id="api_reuse",
        cursor_id=None,
        cursor_type="recheck",
        page=1,
        body=b"ignored-when-hash-matches",
    )
    skipped = repos.save_raw(artifact)
    assert first.status == "succeeded"
    assert skipped is False
    assert len(repos.raw_metadata) == 1


def test_recheck_only_does_not_consume_genre_cursors() -> None:
    seeds = [
        ItemSeed(
            source="rakuten",
            external_item_code="shop:r1",
            active_status="active",
        )
    ]
    client = _client_for(
        {
            "shop:r1": {
                "Items": [
                    {"Item": {"itemCode": "shop:r1", "itemName": "R1", "availability": 1}}
                ]
            },
        }
    )
    # Pre-load a non-recheck response key; job must never call genre/update_sort/etc.
    client.item_search_raw_responses[("genre", "100", 1)] = {
        "Items": [{"Item": {"itemCode": "shop:genre", "itemName": "G"}}]
    }
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)
    result = job.run(job_run_id="job-recheck-only", max_items=10)

    assert result.status == "succeeded"
    assert all(call["cursor_type"] == "recheck" for call in client.item_search_calls)
    assert all(c.cursor_type == "recheck" for c in repos.fetch_cursors.values())
    assert any(c.cursor_status == "exhausted" for c in repos.fetch_cursors.values())
    assert not any(call["cursor_type"] == "genre" for call in client.item_search_calls)


def test_item_and_staging_not_created() -> None:
    seeds = [
        ItemSeed(source="rakuten", external_item_code="shop:x", active_status="active")
    ]
    client = _client_for(
        {
            "shop:x": {
                "Items": [{"Item": {"itemCode": "shop:x", "itemName": "X", "availability": 1}}]
            }
        }
    )
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)
    result = job.run(job_run_id="job-no-item", max_items=5)

    assert result.created_items == []
    assert result.created_staging == []
    assert result.updated_item_rows == []
    assert repos.created_items == []
    assert repos.created_staging == []


def test_phases_tracked() -> None:
    seeds = [
        ItemSeed(source="rakuten", external_item_code="shop:p", active_status="active")
    ]
    client = _client_for(
        {
            "shop:p": {
                "Items": [{"Item": {"itemCode": "shop:p", "itemName": "P", "availability": 1}}]
            }
        }
    )
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)
    result = job.run(job_run_id="job-phases", max_items=5)

    assert "plan" in result.completed_phases
    assert "finalize" in result.completed_phases
    assert set(ITEM_RECHECK_PHASES).issubset(set(result.completed_phases))
    assert any(p["phase"] == "plan" for p in repos.phase_logs)
    assert any(p["phase"] == "finalize" for p in repos.phase_logs)


def test_plan_ordering_and_max_items() -> None:
    older = datetime.now(UTC) - timedelta(days=30)
    newer = datetime.now(UTC) - timedelta(days=1)
    seeds = [
        ItemSeed(
            source="rakuten",
            external_item_code="shop:new-high",
            active_status="active",
            last_checked_at=newer,
            popularity=10.0,
        ),
        ItemSeed(
            source="rakuten",
            external_item_code="shop:old-low",
            active_status="active",
            last_checked_at=older,
            popularity=1.0,
        ),
        ItemSeed(
            source="rakuten",
            external_item_code="shop:inactive",
            active_status="inactive",
        ),
    ]
    client = _client_for(
        {
            "shop:old-low": {
                "Items": [
                    {
                        "Item": {
                            "itemCode": "shop:old-low",
                            "itemName": "Old",
                            "availability": 1,
                        }
                    }
                ]
            },
            "shop:new-high": {
                "Items": [
                    {
                        "Item": {
                            "itemCode": "shop:new-high",
                            "itemName": "New",
                            "availability": 1,
                        }
                    }
                ]
            },
        }
    )
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)
    result = job.run(job_run_id="job-order", max_items=1)

    assert result.planned_item_count == 1
    assert result.succeeded_item_codes == ["shop:old-low"]


def test_adapt_allow_empty_and_availability() -> None:
    empty = adapt_item_search_raw_payload(
        {"Items": []},
        cursor_type="recheck",
        allow_empty=True,
    )
    assert empty.candidates == ()

    with_avail = adapt_item_search_raw_payload(
        {
            "Items": [
                {
                    "Item": {
                        "itemCode": "shop:z",
                        "itemName": "Z",
                        "availability": 0,
                    }
                }
            ]
        },
        cursor_type="recheck",
        allow_empty=False,
    )
    assert with_avail.candidates[0].availability == 0

    # default allow_empty=False still raises on empty (BATCH-003 compat)
    try:
        adapt_item_search_raw_payload({"Items": []}, cursor_type="genre")
        raised = False
    except Exception:  # noqa: BLE001
        raised = True
    assert raised is True


def test_resolve_mapping_unit() -> None:
    from batch.infrastructure.rakuten import AdaptedItemSearchCandidate

    empty = resolve_active_status_candidate(
        batch_run_id="b1",
        external_item_code="shop:e",
        candidates=(),
    )
    assert empty.detection_basis == "empty_hit"

    zero = resolve_active_status_candidate(
        batch_run_id="b1",
        external_item_code="shop:z",
        candidates=(
            AdaptedItemSearchCandidate(
                external_item_code="shop:z",
                availability=0,
            ),
        ),
    )
    assert zero.detection_basis == "availability"
    assert zero.reason_code == "availability_zero"

    ok = resolve_active_status_candidate(
        batch_run_id="b1",
        external_item_code="shop:ok",
        candidates=(
            AdaptedItemSearchCandidate(
                external_item_code="shop:ok",
                availability=None,
            ),
        ),
    )
    assert ok.detection_basis == "api_success"
    assert ok.candidate_active_status == "active"


def test_object_key_helper() -> None:
    key = build_item_search_raw_object_key(
        batch_run_id="job-1",
        api_call_log_id="api_abc",
    )
    assert "item_search" in key
    assert "batch_run_id=job-1" in key
    assert content_hash_for_payload({"a": 1})
