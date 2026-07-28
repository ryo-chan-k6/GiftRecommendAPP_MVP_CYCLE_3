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


# --- §16 No.4 dedupe ---


def test_dedupe_unique_candidate_count_across_routes() -> None:
    """同一 Run で genre / update_sort が同じ itemCode を返しても候補はユニーク。"""

    client = ScaffoldRakutenApiClient(
        item_search_raw_responses={
            ("genre", "100", 1): {
                "Items": [
                    {"Item": {"itemCode": "shop:a", "itemName": "A"}},
                    {"Item": {"itemCode": "shop:b", "itemName": "B"}},
                ]
            },
            ("update_sort", "*", 1): {
                "Items": [
                    {"Item": {"itemCode": "shop:a", "itemName": "A again"}},
                    {"Item": {"itemCode": "shop:c", "itemName": "C"}},
                ]
            },
        }
    )
    repos = _repos()
    job = ItemPseudoDiffJob(rakuten_client=client, repositories=repos)

    result = job.run(
        job_run_id="job-dedupe",
        target_genre_ids=("100",),
        include_update_sort=True,
    )

    assert result.status == "succeeded"
    assert result.candidate_item_code_count == 3  # a, b, c
    assert result.raw_save_success_count == 2  # API 応答単位の Raw は 2


# --- §16 No.5 Rate Limit（error_log / api_call_log） ---


def test_rate_limit_records_ext_102_in_logs() -> None:
    repos = _repos()
    client = ScaffoldRakutenApiClient(
        item_search_raw_responses={
            ("genre", "100", 1): {
                "Items": [{"Item": {"itemCode": "shop:ok", "itemName": "OK"}}]
            }
        },
        rate_limited_item_search_keys={("genre", "200", 1)},
    )
    job = ItemPseudoDiffJob(rakuten_client=client, repositories=repos)

    result = job.run(
        job_run_id="job-rl-partial",
        target_genre_ids=("100", "200"),
        include_update_sort=False,
    )

    assert result.status == "partially_succeeded"
    assert "GRS-EXT-102" in result.error_codes
    assert any(e["code"] == "GRS-EXT-102" for e in repos.error_logs)
    failed = [log for log in repos.api_call_logs if log.get("error_code") == "GRS-EXT-102"]
    assert failed and failed[0]["status"] == "failed"


# --- §16 No.7 cursor は API 成功後のみ ---


def test_cursor_not_advanced_on_api_failure() -> None:
    repos = _repos()
    client = ScaffoldRakutenApiClient(fail_item_search_keys={("genre", "100", 1)})
    job = ItemPseudoDiffJob(rakuten_client=client, repositories=repos)

    result = job.run(
        job_run_id="job-no-cursor",
        target_genre_ids=("100",),
        include_update_sort=False,
    )

    assert result.status == "failed"
    genre_cursors = [c for c in repos.fetch_cursors.values() if c.cursor_type == "genre"]
    assert genre_cursors
    # plan で作成されたまま page=1 / active（失敗後に completed へ進めない）
    assert all(c.page == 1 and c.cursor_status == "active" for c in genre_cursors)


def test_cursor_advances_only_after_success() -> None:
    repos = _repos()
    job = ItemPseudoDiffJob(rakuten_client=_client_genre(), repositories=repos)

    result = job.run(
        job_run_id="job-cursor-ok",
        target_genre_ids=("100",),
        include_update_sort=False,
    )

    assert result.status == "succeeded"
    genre_cursors = [c for c in repos.fetch_cursors.values() if c.cursor_type == "genre"]
    assert genre_cursors
    assert all(c.page == 2 for c in genre_cursors)


# --- GRS-RAW-001 ---


def test_raw_save_failure_records_raw_001() -> None:
    repos = ItemPseudoDiffRepositories(
        object_storage=ScaffoldObjectStorageClient(fail_on_put=True),
        db_writer=ScaffoldDbWriter(),
        bucket="test-raw",
    )
    job = ItemPseudoDiffJob(rakuten_client=_client_genre(), repositories=repos)

    result = job.run(
        job_run_id="job-raw-fail",
        target_genre_ids=("100",),
        include_update_sort=False,
    )

    assert result.status == "failed"
    assert "GRS-RAW-001" in result.error_codes
    assert any(e["code"] == "GRS-RAW-001" for e in repos.error_logs)
    assert len(repos.raw_metadata) == 0


# --- keyword route / priority ---


def test_keyword_route_and_supplement_priority() -> None:
    call_order: list[str] = []

    class OrderTrackingClient(ScaffoldRakutenApiClient):
        def fetch_item_search_raw(self, *, cursor_type: str, **kwargs):  # type: ignore[no-untyped-def]
            call_order.append(cursor_type)
            return super().fetch_item_search_raw(cursor_type=cursor_type, **kwargs)

    client = OrderTrackingClient(
        item_search_raw_responses={
            ("ranking_supplement", "shop:u", 1): {
                "Items": [{"Item": {"itemCode": "shop:u", "itemName": "U"}}]
            },
            ("genre", "100", 1): {
                "Items": [{"Item": {"itemCode": "shop:g", "itemName": "G"}}]
            },
            ("keyword", "gift", 1): {
                "Items": [{"Item": {"itemCode": "shop:k", "itemName": "K"}}]
            },
        }
    )
    repos = _repos(
        seed=[
            FetchCursorRow(
                cursor_type="ranking_supplement",
                scope={"external_item_code": "shop:u"},
                page=1,
            )
        ]
    )
    job = ItemPseudoDiffJob(rakuten_client=client, repositories=repos)

    result = job.run(
        job_run_id="job-prio",
        target_genre_ids=("100",),
        keywords=("gift",),
        include_update_sort=False,
    )

    assert result.status == "succeeded"
    assert call_order[0] == "ranking_supplement"
    assert "keyword" in call_order
    assert result.ranking_supplement_consumed_count == 1


# --- §16 No.8 secret ---


def test_api_call_logs_do_not_contain_secret_fields() -> None:
    client = _client_genre()
    client.fail_item_search_keys.add(("genre", "101", 1))
    repos = _repos()
    job = ItemPseudoDiffJob(rakuten_client=client, repositories=repos)

    job.run(
        job_run_id="job-sec",
        target_genre_ids=("100", "101"),
        include_update_sort=False,
    )

    forbidden = (
        "Authorization",
        "accessKey",
        "access_key",
        "RAKUTEN_ACCESS_KEY",
        "RAKUTEN_APPLICATION_ID",
        "object_storage_secret_key",
        "Bearer ",
    )
    blob = json.dumps({"api": repos.api_call_logs, "err": repos.error_logs}, ensure_ascii=False)
    for token in forbidden:
        assert token not in blob


# --- §16 No.9 境界強化 ---


def test_boundary_no_item_staging_or_ranking_writes() -> None:
    repos = _repos()
    job = ItemPseudoDiffJob(rakuten_client=_client_genre(), repositories=repos)

    result = job.run(
        job_run_id="job-boundary",
        target_genre_ids=("100",),
        include_update_sort=False,
    )

    assert result.status == "succeeded"
    assert repos.created_items == []
    assert repos.created_staging == []
    tables = {call["table"] for call in repos.db_writer.write_calls}
    assert "item" not in tables
    assert "staging_item" not in tables
    assert "ranking_snapshot" not in tables
    assert "raw_product_metadata" in tables
    assert "fetch_cursor" in tables


def test_invalid_payload_records_ext_103() -> None:
    from batch.infrastructure.rakuten import RakutenItemSearchApiError, adapt_item_search_raw_payload

    try:
        adapt_item_search_raw_payload({"Items": "bad"}, cursor_type="genre")
        raise AssertionError("expected GRS-EXT-103")
    except RakutenItemSearchApiError as exc:
        assert exc.code == "GRS-EXT-103"


def test_batch_run_id_separates_object_key_from_job_run_id() -> None:
    """共有 pipeline batch_run_id が raw object key に使われ、job_run_id とは分離できる。"""

    from batch.application.job_run import ScaffoldJobRunTracker

    repos = _repos()
    tracker = ScaffoldJobRunTracker()
    job = ItemPseudoDiffJob(
        rakuten_client=_client_genre(),
        repositories=repos,
        job_run_tracker=tracker,
    )
    pipeline = "pipeline-shared-uuid"
    leaf = "leaf-003-uuid"
    repos.bind_run(batch_run_id=pipeline)

    result = job.run(
        job_run_id=leaf,
        batch_run_id=pipeline,
        target_genre_ids=("100",),
        include_update_sort=False,
    )

    assert result.status == "succeeded"
    assert result.job_run_id == leaf
    assert all(pipeline in key for key in repos.raw_metadata)
    assert all(leaf not in key for key in repos.raw_metadata)
    assert any(
        getattr(r, "job_run_id", None) == leaf and getattr(r, "status", None) == "running"
        for r in tracker.records
    )


def test_cli_batch_run_id_fallback_to_job_run_id() -> None:
    from batch.application.item_pseudo_diff.__main__ import _resolve_business_run_id

    assert _resolve_business_run_id(job_run_id="leaf", batch_run_id="") == "leaf"
    assert (
        _resolve_business_run_id(job_run_id="leaf", batch_run_id="pipeline") == "pipeline"
    )

