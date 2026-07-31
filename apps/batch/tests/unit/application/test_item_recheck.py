"""Unit tests for BATCH-004 楽天既存商品再確認（仕様書 §16 No.1〜9）."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

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
from batch.application.item_recheck.models import RawItemSearchArtifact, ResolvedCandidate
from batch.infrastructure.db import ScaffoldDbWriter
from batch.infrastructure.object_storage import ScaffoldObjectStorageClient
from batch.infrastructure.rakuten import (
    RakutenItemSearchApiError,
    ScaffoldRakutenApiClient,
    adapt_item_search_raw_payload,
)

_FORBIDDEN_SECRET_TOKENS = (
    "Authorization",
    "accessKey",
    "access_key",
    "RAKUTEN_ACCESS_KEY",
    "RAKUTEN_APPLICATION_ID",
    "object_storage_secret_key",
    "Bearer ",
)


def _repos(
    *,
    seeds: list[ItemSeed] | None = None,
    fail_on_put: bool = False,
) -> ItemRecheckRepositories:
    return ItemRecheckRepositories(
        object_storage=ScaffoldObjectStorageClient(fail_on_put=fail_on_put),
        db_writer=ScaffoldDbWriter(),
        bucket="test-raw",
        seed_items=list(seeds or []),
    )


def _client_for(codes: dict[str, dict[str, object]]) -> ScaffoldRakutenApiClient:
    responses = {("recheck", code, 1): payload for code, payload in codes.items()}
    return ScaffoldRakutenApiClient(item_search_raw_responses=responses)


def _ok_payload(code: str, *, availability: int = 1) -> dict[str, object]:
    return {
        "Items": [
            {
                "Item": {
                    "itemCode": code,
                    "itemName": f"Item {code}",
                    "availability": availability,
                }
            }
        ]
    }


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


# --- §16 No.1: 正常系で Raw / Metadata / cursor が進む ---


def test_happy_path_advances_recheck_cursor() -> None:
    """§16 No.1: API 成功後に recheck cursor が exhausted へ進む。"""

    seeds = [
        ItemSeed(source="rakuten", external_item_code="shop:ok", active_status="active")
    ]
    client = _client_for({"shop:ok": _ok_payload("shop:ok")})
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-cursor-ok", max_items=10)

    assert result.status == "succeeded"
    assert len(repos.raw_metadata) == 1
    cursors = [c for c in repos.fetch_cursors.values() if c.cursor_type == "recheck"]
    assert len(cursors) == 1
    assert cursors[0].cursor_status == "exhausted"
    assert cursors[0].page == 2
    assert cursors[0].scope.get("external_item_code") == "shop:ok"


# --- §16 No.2: 1 external_item_code = 1 カーソル ---


def test_recheck_cursor_get_or_create_uniqueness() -> None:
    """§16 No.2: 同一 external_item_code は get-or-create で 1 カーソル。"""

    repos = _repos()
    first = repos.get_or_create_recheck_cursor(external_item_code="shop:uniq")
    second = repos.get_or_create_recheck_cursor(external_item_code="shop:uniq")
    other = repos.get_or_create_recheck_cursor(external_item_code="shop:other")

    assert first.cursor_id == second.cursor_id
    assert first.cursor_id != other.cursor_id
    recheck = [c for c in repos.fetch_cursors.values() if c.cursor_type == "recheck"]
    assert len(recheck) == 2


def test_recheck_cursor_unique_across_job_runs() -> None:
    """§16 No.2: 複数 Run でも同一商品は同一 fingerprint のカーソルを再利用する。"""

    seeds = [
        ItemSeed(source="rakuten", external_item_code="shop:reuse", active_status="active")
    ]
    client = _client_for({"shop:reuse": _ok_payload("shop:reuse")})
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)

    job.run(job_run_id="job-reuse-1", max_items=10)
    ids_after_first = {
        c.cursor_id for c in repos.fetch_cursors.values() if c.cursor_type == "recheck"
    }
    job.run(job_run_id="job-reuse-2", max_items=10)
    ids_after_second = {
        c.cursor_id for c in repos.fetch_cursors.values() if c.cursor_type == "recheck"
    }

    assert ids_after_first == ids_after_second
    assert len(ids_after_second) == 1


# --- §16 No.4: candidate upsert ON CONFLICT 再検出 ---


def test_candidate_upsert_resets_to_detected_on_conflict() -> None:
    """§16 No.4: 同一冪等キー再 upsert で detected / applied_at=None に戻る。"""

    repos = _repos()
    key_run = "job-redetect"
    code = "shop:re"
    prior = ResolvedCandidate(
        batch_run_id=key_run,
        source="rakuten",
        external_item_code=code,
        candidate_active_status="unavailable",
        reason_code="empty_hit",
        detection_basis="empty_hit",
        candidate_status="applied",
        applied_at=datetime.now(UTC),
        item_id="item_re",
    )
    repos.upsert_candidate(prior)
    prior_row = repos.candidates[(key_run, "rakuten", code)]
    # Simulate applied state that ON CONFLICT must clear
    prior_row["candidate_status"] = "applied"
    prior_row["applied_at"] = datetime.now(UTC)
    prior_id = prior_row["item_active_status_candidate_id"]

    seeds = [
        ItemSeed(
            source="rakuten",
            external_item_code=code,
            item_id="item_re",
            active_status="active",
        )
    ]
    client = _client_for({code: _ok_payload(code)})
    repos.seed_items = list(seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)
    result = job.run(job_run_id=key_run, max_items=10)

    assert result.status == "succeeded"
    row = repos.candidates[(key_run, "rakuten", code)]
    assert row["item_active_status_candidate_id"] == prior_id
    assert row["candidate_status"] == "detected"
    assert row["applied_at"] is None
    assert row["detection_basis"] == "api_success"
    assert row["candidate_active_status"] == "active"
    assert result.updated_item_rows == []


# --- §16 No.5: Rate Limit ---


def test_rate_limit_records_ext_102() -> None:
    """§16 No.5: 429 相当で GRS-EXT-102 を記録し、cursor を paused へ遷移する。"""

    seeds = [
        ItemSeed(source="rakuten", external_item_code="shop:rl", active_status="active")
    ]
    client = ScaffoldRakutenApiClient(
        rate_limited_item_search_keys={("recheck", "shop:rl", 1)},
    )
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-rl", max_items=10)

    assert result.status == "failed"
    assert "GRS-EXT-102" in result.error_codes
    assert any(e["code"] == "GRS-EXT-102" for e in repos.error_logs)
    failed = [log for log in repos.api_call_logs if log.get("error_code") == "GRS-EXT-102"]
    assert failed and failed[0]["status"] == "rate_limited"
    assert failed[0].get("fetch_cursor_id")
    cursors = list(repos.fetch_cursors.values())
    assert cursors
    assert all(c.cursor_status == "paused" and c.page == 1 for c in cursors)


def test_rate_limit_partial_with_success() -> None:
    """§16 No.5 / No.6: Rate Limit と成功が混在すると partially_succeeded。RL のみ paused。"""

    seeds = [
        ItemSeed(source="rakuten", external_item_code="shop:ok", active_status="active"),
        ItemSeed(source="rakuten", external_item_code="shop:rl", active_status="active"),
    ]
    client = ScaffoldRakutenApiClient(
        item_search_raw_responses={("recheck", "shop:ok", 1): _ok_payload("shop:ok")},
        rate_limited_item_search_keys={("recheck", "shop:rl", 1)},
    )
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-rl-partial", max_items=10)

    assert result.status == "partially_succeeded"
    assert "GRS-EXT-102" in result.error_codes
    assert "GRS-BAT-002" in result.error_codes
    assert "shop:ok" in result.succeeded_item_codes
    assert "shop:rl" in result.failed_item_codes
    by_code = {
        (c.scope.get("external_item_code") if isinstance(c.scope, dict) else None): c
        for c in repos.fetch_cursors.values()
    }
    assert by_code["shop:ok"].cursor_status == "exhausted"
    assert by_code["shop:rl"].cursor_status == "paused"
    assert by_code["shop:rl"].page == 1


def test_non_rate_limit_api_failure_does_not_pause_cursor() -> None:
    """GRS-EXT-100 等では paused にせず、cursor は active のまま（再試行可能）。"""

    seeds = [
        ItemSeed(source="rakuten", external_item_code="shop:bad", active_status="active")
    ]
    client = ScaffoldRakutenApiClient(
        fail_item_search_keys={("recheck", "shop:bad", 1)},
    )
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-no-pause", max_items=10)

    assert result.status == "failed"
    assert "GRS-EXT-100" in result.error_codes
    cursors = list(repos.fetch_cursors.values())
    assert cursors
    assert all(c.cursor_status == "active" and c.page == 1 for c in cursors)
    assert not any(c.cursor_status == "paused" for c in cursors)


def test_api_failure_partial_records_ext_100_and_bat_002() -> None:
    """§16 No.6: 外部API失敗で api_call_log / error_log と部分失敗方針。"""

    seeds = [
        ItemSeed(source="rakuten", external_item_code="shop:ok", active_status="active"),
        ItemSeed(source="rakuten", external_item_code="shop:bad", active_status="active"),
    ]
    client = ScaffoldRakutenApiClient(
        item_search_raw_responses={("recheck", "shop:ok", 1): _ok_payload("shop:ok")},
        fail_item_search_keys={("recheck", "shop:bad", 1)},
    )
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-api-partial", max_items=10)

    assert result.status == "partially_succeeded"
    assert "GRS-EXT-100" in result.error_codes
    assert "GRS-BAT-002" in result.error_codes
    assert any(e["code"] == "GRS-EXT-100" for e in repos.error_logs)
    failed_logs = [log for log in repos.api_call_logs if log.get("error_code") == "GRS-EXT-100"]
    assert failed_logs and failed_logs[0]["status"] == "failed"
    assert failed_logs[0].get("fetch_cursor_id")
    assert "shop:ok" in result.succeeded_item_codes
    assert "shop:bad" in result.failed_item_codes


# --- §16 No.7: cursor は API 成功後のみ ---


def test_cursor_not_advanced_on_api_failure() -> None:
    """§16 No.7: API 失敗時は fetch_cursor を exhausted に進めない。"""

    seeds = [
        ItemSeed(source="rakuten", external_item_code="shop:fail", active_status="active")
    ]
    client = ScaffoldRakutenApiClient(
        fail_item_search_keys={("recheck", "shop:fail", 1)},
    )
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-no-cursor", max_items=10)

    assert result.status == "failed"
    assert "GRS-EXT-100" in result.error_codes
    cursors = [c for c in repos.fetch_cursors.values() if c.cursor_type == "recheck"]
    assert cursors
    assert all(c.page == 1 and c.cursor_status == "active" for c in cursors)


def test_cursor_not_advanced_on_raw_save_failure() -> None:
    """§16 No.7 / GRS-RAW-001: Raw 失敗時は cursor_update に到達しない。"""

    seeds = [
        ItemSeed(source="rakuten", external_item_code="shop:raw", active_status="active")
    ]
    client = _client_for({"shop:raw": _ok_payload("shop:raw")})
    repos = _repos(seeds=seeds, fail_on_put=True)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-raw-fail", max_items=10)

    assert result.status == "failed"
    assert "GRS-RAW-001" in result.error_codes
    assert any(e["code"] == "GRS-RAW-001" for e in repos.error_logs)
    assert len(repos.raw_metadata) == 0
    cursors = list(repos.fetch_cursors.values())
    assert cursors
    assert all(c.page == 1 and c.cursor_status == "active" for c in cursors)


# --- §16 No.8: secret 非含有 ---


def test_api_call_logs_do_not_contain_secret_fields() -> None:
    """§16 No.8: api_call_log / error_log に secret フィールドが無い。"""

    seeds = [
        ItemSeed(source="rakuten", external_item_code="shop:ok", active_status="active"),
        ItemSeed(source="rakuten", external_item_code="shop:bad", active_status="active"),
    ]
    client = ScaffoldRakutenApiClient(
        item_search_raw_responses={("recheck", "shop:ok", 1): _ok_payload("shop:ok")},
        fail_item_search_keys={("recheck", "shop:bad", 1)},
    )
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)
    job.run(job_run_id="job-sec", max_items=10)

    blob = json.dumps(
        {"api": repos.api_call_logs, "err": repos.error_logs, "raw": list(repos.raw_metadata.values())},
        ensure_ascii=False,
        default=str,
    )
    for token in _FORBIDDEN_SECRET_TOKENS:
        assert token not in blob
    for log in repos.api_call_logs:
        for key in log:
            assert key.lower() not in {
                "authorization",
                "accesskey",
                "access_key",
                "rakuten_access_key",
                "rakuten_application_id",
            }


# --- api_call_log.fetch_cursor_id / external_item_codes / invalid payload ---


def test_api_call_log_has_fetch_cursor_id() -> None:
    seeds = [
        ItemSeed(source="rakuten", external_item_code="shop:link", active_status="active")
    ]
    client = _client_for({"shop:link": _ok_payload("shop:link")})
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-cursor-link", max_items=10)

    assert result.status == "succeeded"
    assert repos.api_call_logs
    assert all(log.get("fetch_cursor_id") for log in repos.api_call_logs)


def test_explicit_external_item_codes_override() -> None:
    """§9.2 / §18.1 No.6: 明示リストは優先度を上書きし、未 seed コードも再確認可能。"""

    older = datetime.now(UTC) - timedelta(days=30)
    seeds = [
        ItemSeed(
            source="rakuten",
            external_item_code="shop:old",
            active_status="active",
            last_checked_at=older,
            popularity=1.0,
        ),
        ItemSeed(
            source="rakuten",
            external_item_code="shop:seeded",
            active_status="active",
            last_checked_at=older,
            popularity=1.0,
        ),
    ]
    client = _client_for(
        {
            "shop:seeded": _ok_payload("shop:seeded"),
            "shop:explicit-new": _ok_payload("shop:explicit-new"),
        }
    )
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)

    result = job.run(
        job_run_id="job-explicit",
        max_items=10,
        external_item_codes=("shop:explicit-new", "shop:seeded"),
    )

    assert result.status == "succeeded"
    assert result.succeeded_item_codes == ["shop:explicit-new", "shop:seeded"]
    assert "shop:old" not in result.succeeded_item_codes
    assert result.planned_item_count == 2


def test_invalid_payload_via_job_records_ext_103() -> None:
    """malformed Items は allow_empty=True でも GRS-EXT-103（job 経由）。"""

    seeds = [
        ItemSeed(source="rakuten", external_item_code="shop:bad-json", active_status="active")
    ]
    client = _client_for({"shop:bad-json": {"Items": "bad"}})
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-malformed", max_items=10)

    assert result.status == "failed"
    assert "GRS-EXT-103" in result.error_codes
    assert any(e["code"] == "GRS-EXT-103" for e in repos.error_logs)
    failed = [log for log in repos.api_call_logs if log.get("error_code") == "GRS-EXT-103"]
    assert failed and failed[0]["status"] == "failed"
    cursors = list(repos.fetch_cursors.values())
    assert all(c.cursor_status == "active" and c.page == 1 for c in cursors)


def test_invalid_payload_allow_empty_false_raises_ext_103() -> None:
    """allow_empty=False 経路（BATCH-003 互換）でも malformed は GRS-EXT-103。"""

    try:
        adapt_item_search_raw_payload({"Items": "bad"}, cursor_type="genre")
        raise AssertionError("expected GRS-EXT-103")
    except RakutenItemSearchApiError as exc:
        assert exc.code == "GRS-EXT-103"


def test_boundary_db_writes_exclude_item_and_staging() -> None:
    """§16 No.9: item / staging_item へ write しない。"""

    seeds = [
        ItemSeed(source="rakuten", external_item_code="shop:b", active_status="active")
    ]
    client = _client_for({"shop:b": _ok_payload("shop:b")})
    repos = _repos(seeds=seeds)
    job = ItemRecheckJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-boundary", max_items=5)

    assert result.status == "succeeded"
    write_tables = {call["table"] for call in repos.db_writer.write_calls}
    upsert_tables = {call["table"] for call in repos.db_writer.upsert_calls}
    tables = write_tables | upsert_tables
    assert "item" not in tables
    assert "staging_item" not in tables
    assert "raw_product_metadata" in write_tables
    assert "fetch_cursor" in write_tables
    assert "item_active_status_candidate" in upsert_tables


def test_list_seedable_items_uses_db_reader_when_injected() -> None:
    """Wave A': DbReader 注入時は seed_items ではなく SELECT 経路を使う。"""

    from batch.infrastructure.db import ScaffoldDbReader

    older = datetime.now(UTC) - timedelta(days=30)
    newer = datetime.now(UTC) - timedelta(days=1)
    reader = ScaffoldDbReader()
    reader.seed(
        "item",
        (
            {
                "item_id": "i1",
                "source": "rakuten",
                "external_item_code": "shop:new",
                "active_status": "active",
                "last_checked_at": newer,
            },
            {
                "item_id": "i2",
                "source": "rakuten",
                "external_item_code": "shop:old",
                "active_status": "active",
                "last_checked_at": older,
            },
            {
                "item_id": "i3",
                "source": "rakuten",
                "external_item_code": "shop:inactive",
                "active_status": "inactive",
                "last_checked_at": older,
            },
        ),
    )
    repos = ItemRecheckRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=ScaffoldDbWriter(),
        db_reader=reader,
        bucket="test-raw",
        seed_items=[],
    )

    selected = repos.list_seedable_items(max_items=10)
    assert [s.external_item_code for s in selected] == ["shop:old", "shop:new"]
    assert reader.fetch_calls
    assert reader.fetch_calls[0]["table"] == "item"
    assert ("active_status", "active") in reader.fetch_calls[0]["equals"]


def test_list_seedable_items_db_reader_explicit_codes() -> None:
    from batch.infrastructure.db import ScaffoldDbReader

    reader = ScaffoldDbReader()
    reader.seed(
        "item",
        (
            {
                "item_id": "i1",
                "source": "rakuten",
                "external_item_code": "shop:known",
                "active_status": "active",
                "last_checked_at": None,
            },
        ),
    )
    repos = ItemRecheckRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=ScaffoldDbWriter(),
        db_reader=reader,
        bucket="test-raw",
    )

    selected = repos.list_seedable_items(
        max_items=5,
        external_item_codes=("shop:known", "shop:synthetic"),
    )
    assert [s.external_item_code for s in selected] == ["shop:known", "shop:synthetic"]
    assert selected[1].item_id is None


def test_cli_non_demo_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    from dataclasses import replace

    from batch.application.item_recheck import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(scaffold_batch_settings(), database_url=None),
    )
    code = cli.main(["--job-run-id", "no-db", "--live-rakuten"])
    assert code == 2


def test_cli_non_demo_uses_db_reader_before_rakuten_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DATABASE_URL 無しは楽天ゲートより先に exit 2（seed SELECT 前提）。"""

    from dataclasses import replace

    from batch.application.item_recheck import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(scaffold_batch_settings(), database_url=""),
    )
    code = cli.main(["--job-run-id", "no-db"])
    assert code == 2
