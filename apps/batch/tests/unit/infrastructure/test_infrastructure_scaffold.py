import json
from datetime import UTC, datetime

from batch.application.raw_staging.models import RawMetadataSeed
from batch.application.raw_staging.transform import transform_raw
from batch.application.raw_staging.validate import validate_transform_result
from batch.infrastructure import (
    DbWriteResult,
    LogContext,
    ObjectRef,
    RakutenGenre,
    RakutenItem,
    RakutenRankingEntry,
    ScaffoldBatchLogger,
    ScaffoldDbWriter,
    ScaffoldExternalAiClient,
    ScaffoldObjectStorageClient,
    ScaffoldRakutenApiClient,
    StoredObject,
)


def test_scaffold_db_writer_records_writes() -> None:
    writer = ScaffoldDbWriter()
    rows = ({"item_code": "item-1"}, {"item_code": "item-2"})

    result = writer.write_rows("items", rows)

    assert result == DbWriteResult(rows_affected=2, table="items")
    assert writer.write_calls == [{"table": "items", "rows": rows}]


def test_scaffold_rakuten_client_records_api_calls() -> None:
    client = ScaffoldRakutenApiClient(
        items=(RakutenItem(item_code="item-1", item_name="Gift"),),
        ranking=(RakutenRankingEntry(rank=1, item_code="item-1"),),
        genres={"100": RakutenGenre(genre_id="100", genre_name="Gifts")},
    )

    items = client.search_items(keyword="gift", page=2)
    ranking = client.fetch_ranking(genre_id="100", page=1)
    genre = client.fetch_genre(genre_id="100")

    assert items[0].item_code == "item-1"
    assert ranking[0].rank == 1
    assert genre == RakutenGenre(genre_id="100", genre_name="Gifts")
    assert client.search_calls == [{"keyword": "gift", "page": 2}]
    assert client.ranking_calls == [{"genre_id": "100", "page": 1}]
    assert client.genre_calls == [{"genre_id": "100"}]


def test_scaffold_item_search_fallback_includes_staging_required_fields(
    capsys,
) -> None:
    """map 外 page でも itemUrl 等を含め、stderr に fallback 警告を出す。"""

    client = ScaffoldRakutenApiClient(
        items=(RakutenItem(item_code="shop:gift-1", item_name="Gift One"),),
    )

    raw = client.fetch_item_search_raw(
        cursor_type="genre",
        genre_id="100",
        page=2,
    )

    item = raw["Items"][0]["Item"]  # type: ignore[index]
    assert isinstance(item, dict)
    assert item["itemCode"] == "shop:gift-1"
    assert item["itemUrl"] == "https://item.example/shop:gift-1"
    assert item["itemPrice"] == 1000
    assert item["genreId"] == 100
    assert item["shopCode"] == "shop"
    assert item["mediumImageUrls"]
    err = capsys.readouterr().err
    assert "scaffold item_search fallback" in err
    assert "page=2" in err


def test_scaffold_item_search_fallback_passes_raw_staging(capsys) -> None:
    """page>=2 fallback Raw が BATCH-005 validate / staging まで通る。"""

    client = ScaffoldRakutenApiClient(
        items=(RakutenItem(item_code="shop:gift-2", item_name="Gift Two"),),
    )
    raw = client.fetch_item_search_raw(
        cursor_type="genre",
        genre_id="100",
        page=2,
    )
    body = json.dumps(raw, ensure_ascii=False).encode("utf-8")
    meta = RawMetadataSeed(
        raw_metadata_id="rm_fb",
        object_key="raw/rakuten/item_search/rm_fb.json",
        content_hash="deadbeef",
        source="rakuten",
        source_api="item_search",
        import_status="raw_saved",
    )
    transformed = transform_raw(meta=meta, body=body, staged_at=datetime.now(UTC))
    validated = validate_transform_result(transformed)
    assert validated.items
    assert validated.items[0].item.item_url.startswith("https://")
    assert "scaffold item_search fallback" in capsys.readouterr().err


def test_scaffold_object_storage_put_and_get() -> None:
    client = ScaffoldObjectStorageClient()
    ref = ObjectRef(bucket="raw", key="rakuten/items/page-1.json")

    stored = client.put_object(ref, body=b"{}", content_type="application/json")
    fetched = client.get_object(ref)

    assert stored == StoredObject(ref=ref, content_type="application/json", body=b"{}")
    assert fetched == stored
    assert len(client.put_calls) == 1
    assert client.get_calls == [ref]


def test_scaffold_external_ai_returns_marker_response() -> None:
    client = ScaffoldExternalAiClient()

    response = client.generate("embedding input", purpose="item_embedding")

    assert response.text == "[scaffold:item_embedding]"
    assert response.model == "scaffold"
    assert client.generate_calls == [
        {
            "prompt": "embedding input",
            "purpose": "item_embedding",
        }
    ]


def test_scaffold_logger_records_context_and_attributes() -> None:
    logger = ScaffoldBatchLogger(
        context=LogContext(trace_id="trace-1", job_run_id="job-1"),
    )

    bound = logger.bind(job_run_id="job-2")
    bound.info("collector_started", batch_id="BATCH-003")
    logger.error("collector_failed", reason="scaffold")

    assert len(logger.records) == 2
    assert logger.records[0].event == "collector_started"
    assert logger.records[0].context.trace_id == "trace-1"
    assert logger.records[0].context.job_run_id == "job-2"
    assert logger.records[0].attributes == {"batch_id": "BATCH-003"}
    assert logger.records[1].level == "error"
    assert logger.records[1].event == "collector_failed"
