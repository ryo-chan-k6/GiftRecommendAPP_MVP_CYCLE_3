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
