"""Minimal unit tests for BATCH-002 楽天ランキングスナップショット."""

from __future__ import annotations

import json
from datetime import date

import pytest

from batch.application.ranking_snapshot import (
    BATCH_ID,
    RANKING_SNAPSHOT_PHASES,
    RankingSnapshotJob,
    RankingSnapshotRepositories,
    build_ranking_raw_object_key,
    content_hash_for_payload,
    popularity_signal_idempotency_key,
    ranking_snapshot_idempotency_key,
)
from batch.infrastructure.db import ScaffoldDbWriter
from batch.infrastructure.object_storage import ScaffoldObjectStorageClient
from batch.infrastructure.rakuten import (
    RakutenRankingApiError,
    RakutenRankingEntry,
    ScaffoldRakutenApiClient,
    adapt_ranking_raw_payload,
)


def _repos(*, known_item_codes: set[str] | None = None) -> RankingSnapshotRepositories:
    return RankingSnapshotRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=ScaffoldDbWriter(),
        bucket="test-raw",
        known_item_codes=known_item_codes or set(),
    )


def _client_with_ranking(
    *,
    genre_id: str = "100",
    period: str = "daily",
    last_build_date: str = "2026-07-13T12:00:00+0900",
    items: list[dict[str, object]] | None = None,
) -> ScaffoldRakutenApiClient:
    payload_items = items or [
        {"rank": 1, "itemCode": "shop:a"},
        {"rank": 2, "itemCode": "shop:b"},
    ]
    return ScaffoldRakutenApiClient(
        ranking=tuple(
            RakutenRankingEntry(rank=int(i["rank"]), item_code=str(i["itemCode"]))  # type: ignore[arg-type]
            for i in payload_items
        ),
        ranking_raw_responses={
            (genre_id, period, 1): {
                "lastBuildDate": last_build_date,
                "genreId": genre_id,
                "Items": payload_items,
            }
        },
    )


def test_ranking_snapshot_happy_path() -> None:
    repos = _repos(known_item_codes={"shop:a", "shop:b"})
    job = RankingSnapshotJob(rakuten_client=_client_with_ranking(), repositories=repos)

    result = job.run(job_run_id="job-1", target_genre_ids=("100",), period="daily")

    assert result.batch_id == BATCH_ID
    assert result.status == "succeeded"
    assert result.succeeded_genre_ids == ["100"]
    assert result.failed_genre_ids == []
    assert result.snapshot_count == 1
    assert result.popularity_signal_upsert_count == 2
    assert len(repos.snapshots) == 1
    assert len(repos.popularity_signals) == 2
    assert len(repos.raw_metadata) == 1
    assert all(
        meta.get("source_api") == "item_ranking" for meta in repos.raw_metadata.values()
    )
    assert "plan" in result.completed_phases
    assert "finalize" in result.completed_phases
    assert set(RANKING_SNAPSHOT_PHASES).issubset(set(result.completed_phases))


def test_ranking_snapshot_is_idempotent_on_rerun() -> None:
    repos = _repos(known_item_codes={"shop:a", "shop:b"})
    client = _client_with_ranking()
    job = RankingSnapshotJob(rakuten_client=client, repositories=repos)

    first = job.run(job_run_id="job-2a", target_genre_ids=("100",), period="daily")
    second = job.run(job_run_id="job-2b", target_genre_ids=("100",), period="daily")

    assert first.status == "succeeded"
    assert second.status == "succeeded"
    assert len(repos.snapshots) == 1
    key = ranking_snapshot_idempotency_key(
        source="rakuten",
        external_genre_id="100",
        period="daily",
        last_build_date="2026-07-13T12:00:00+0900",
    )
    assert key in repos.snapshots
    signal_keys = list(repos.popularity_signals.keys())
    assert len(signal_keys) == len(set(signal_keys))
    assert len(repos.popularity_signals) == 2
    snapshot_id = repos.snapshots[key].ranking_snapshot_id
    assert snapshot_id is not None
    assert popularity_signal_idempotency_key(ranking_snapshot_id=snapshot_id, rank=1) in (
        repos.popularity_signals
    )


def test_ranking_snapshot_partial_failure_on_api_error() -> None:
    client = ScaffoldRakutenApiClient(
        ranking_raw_responses={
            ("100", "daily", 1): {
                "lastBuildDate": "2026-07-13T12:00:00+0900",
                "genreId": "100",
                "Items": [{"rank": 1, "itemCode": "shop:a"}],
            }
        },
        fail_ranking_keys={("101", "daily", 1)},
    )
    repos = _repos(known_item_codes={"shop:a"})
    job = RankingSnapshotJob(rakuten_client=client, repositories=repos)

    result = job.run(
        job_run_id="job-3",
        target_genre_ids=("100", "101"),
        period="daily",
    )

    assert result.status == "partially_succeeded"
    assert result.succeeded_genre_ids == ["100"]
    assert result.failed_genre_ids == ["101"]
    assert "GRS-EXT-100" in result.error_codes
    assert "GRS-BAT-002" in result.error_codes
    assert len(repos.snapshots) == 1
    failed_api = [log for log in repos.api_call_logs if log["genre_id"] == "101"]
    assert failed_api and failed_api[0]["status"] == "failed"
    assert failed_api[0]["error_code"] == "GRS-EXT-100"


def test_unknown_item_code_records_candidate_without_creating_item() -> None:
    repos = _repos(known_item_codes={"shop:known"})
    client = _client_with_ranking(
        items=[
            {"rank": 1, "itemCode": "shop:known"},
            {"rank": 2, "itemCode": "shop:unknown"},
        ]
    )
    job = RankingSnapshotJob(rakuten_client=client, repositories=repos)

    result = job.run(job_run_id="job-unk", target_genre_ids=("100",), period="daily")

    assert result.status == "succeeded"
    assert result.unknown_item_count == 1
    assert "shop:unknown" in repos.unknown_items
    unknown_signal = next(
        s for s in repos.popularity_signals.values() if s.external_item_code == "shop:unknown"
    )
    assert unknown_signal.item_id is None
    known_signal = next(
        s for s in repos.popularity_signals.values() if s.external_item_code == "shop:known"
    )
    assert known_signal.item_id == "item:shop:known"
    assert repos.created_items == []
    assert repos.unknown_items["shop:unknown"].cursor_type == "ranking_supplement"


def test_adapt_ranking_raw_payload_maps_items() -> None:
    payload = {
        "lastBuildDate": "2026-07-13T09:00:00+0900",
        "genreId": "200",
        "Items": [
            {"rank": 1, "itemCode": "a:1"},
            {"Item": {"rank": 2, "itemCode": "b:2"}},
        ],
    }

    adapted = adapt_ranking_raw_payload(payload, requested_genre_id="200", period="daily")

    assert adapted.last_build_date == "2026-07-13T09:00:00+0900"
    assert adapted.genre_id == "200"
    assert adapted.entries == (
        RakutenRankingEntry(rank=1, item_code="a:1"),
        RakutenRankingEntry(rank=2, item_code="b:2"),
    )


def test_adapt_ranking_invalid_payload_raises_ext_103() -> None:
    with pytest.raises(RakutenRankingApiError) as exc_info:
        adapt_ranking_raw_payload({"Items": []}, requested_genre_id="100")

    assert exc_info.value.code == "GRS-EXT-103"


def test_raw_object_key_uses_item_ranking_prefix() -> None:
    key = build_ranking_raw_object_key(
        batch_run_id="bat_002",
        api_call_log_id="api_001",
        fetched_on=date(2026, 7, 13),
    )
    assert key == "raw/rakuten/item_ranking/dt=2026-07-13/batch_run_id=bat_002/api_001.json"
    payload = {"lastBuildDate": "x", "Items": [{"rank": 1, "itemCode": "a"}]}
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    assert content_hash_for_payload(payload) == content_hash_for_payload(body)


def test_api_call_logs_do_not_contain_secret_fields() -> None:
    client = _client_with_ranking()
    client.fail_ranking_keys.add(("101", "daily", 1))
    repos = _repos(known_item_codes={"shop:a", "shop:b"})
    job = RankingSnapshotJob(rakuten_client=client, repositories=repos)

    job.run(job_run_id="job-sec", target_genre_ids=("100", "101"), period="daily")

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


# --- §16 No.5 Rate Limit ---


def test_ranking_snapshot_rate_limit_records_ext_102() -> None:
    client = _client_with_ranking()
    client.rate_limited_ranking_keys.add(("101", "daily", 1))
    # Ensure 100 succeeds
    client.ranking_raw_responses[("101", "daily", 1)] = {
        "lastBuildDate": "2026-07-13T12:00:00+0900",
        "genreId": "101",
        "Items": [{"rank": 1, "itemCode": "shop:x"}],
    }
    repos = _repos(known_item_codes={"shop:a", "shop:b", "shop:x"})
    job = RankingSnapshotJob(rakuten_client=client, repositories=repos)

    result = job.run(
        job_run_id="job-rl",
        target_genre_ids=("100", "101"),
        period="daily",
    )

    assert result.status == "partially_succeeded"
    assert result.succeeded_genre_ids == ["100"]
    assert result.failed_genre_ids == ["101"]
    assert "GRS-EXT-102" in result.error_codes
    assert any(e["code"] == "GRS-EXT-102" for e in repos.error_logs)
    failed_api = [log for log in repos.api_call_logs if log["genre_id"] == "101"]
    assert failed_api and failed_api[0]["status"] == "failed"
    assert failed_api[0]["error_code"] == "GRS-EXT-102"


# --- §16 No.7 Raw失敗 ---


def test_ranking_snapshot_raw_save_failure_records_raw_001() -> None:
    repos = RankingSnapshotRepositories(
        object_storage=ScaffoldObjectStorageClient(fail_on_put=True),
        db_writer=ScaffoldDbWriter(),
        bucket="test-raw",
        known_item_codes={"shop:a", "shop:b"},
    )
    job = RankingSnapshotJob(rakuten_client=_client_with_ranking(), repositories=repos)

    result = job.run(job_run_id="job-raw", target_genre_ids=("100",), period="daily")

    assert result.status == "failed"
    assert result.failed_genre_ids == ["100"]
    assert "GRS-RAW-001" in result.error_codes
    assert "GRS-BAT-001" in result.error_codes
    assert len(repos.snapshots) == 0
    assert any(e["code"] == "GRS-RAW-001" for e in repos.error_logs)


def test_ranking_snapshot_all_failures_marks_failed() -> None:
    client = ScaffoldRakutenApiClient(
        fail_ranking_keys={("100", "daily", 1), ("101", "daily", 1)},
    )
    repos = _repos()
    job = RankingSnapshotJob(rakuten_client=client, repositories=repos)

    result = job.run(
        job_run_id="job-all-fail",
        target_genre_ids=("100", "101"),
        period="daily",
    )

    assert result.status == "failed"
    assert result.succeeded_genre_ids == []
    assert set(result.failed_genre_ids) == {"100", "101"}
    assert "GRS-EXT-100" in result.error_codes
    assert "GRS-BAT-001" in result.error_codes


def test_ranking_snapshot_persists_staging_rows() -> None:
    """§16 No.1 補強: Staging も更新されること。"""

    repos = _repos(known_item_codes={"shop:a", "shop:b"})
    job = RankingSnapshotJob(rakuten_client=_client_with_ranking(), repositories=repos)

    result = job.run(job_run_id="job-stg", target_genre_ids=("100",), period="daily")

    assert result.status == "succeeded"
    assert len(repos.staging_rankings) == 2
    assert all(row.external_genre_id == "100" for row in repos.staging_rankings.values())


def test_batch_settings_repr_masks_access_keys() -> None:
    from batch.config._scaffold import scaffold_batch_settings

    settings = scaffold_batch_settings()
    text = repr(settings)
    assert "scaffold-rakuten-access-key" not in text
    assert "rakuten_access_key='***'" in text
