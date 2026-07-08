from reco.infrastructure import (
    DatabaseHealth,
    LogContext,
    ScaffoldDatabaseSession,
    ScaffoldExternalAiClient,
    ScaffoldRecoLogger,
    ScaffoldVectorStoreClient,
    VectorSearchResult,
)


def test_scaffold_database_session_reports_health() -> None:
    session = ScaffoldDatabaseSession()

    health = session.health_check()

    assert health == DatabaseHealth(is_available=True, backend="scaffold")


def test_scaffold_vector_store_records_search_calls() -> None:
    client = ScaffoldVectorStoreClient(
        results=(
            VectorSearchResult(item_id="item-1", score=0.9),
            VectorSearchResult(item_id="item-2", score=0.8),
        )
    )

    results = client.search((0.1, 0.2, 0.3), top_k=1)

    assert len(results) == 1
    assert results[0].item_id == "item-1"
    assert client.search_calls == [
        {
            "query_embedding": (0.1, 0.2, 0.3),
            "top_k": 1,
        }
    ]


def test_scaffold_external_ai_returns_marker_response() -> None:
    client = ScaffoldExternalAiClient()

    response = client.generate("prompt text", purpose="semantic_extract")

    assert response.text == "[scaffold:semantic_extract]"
    assert response.model == "scaffold"
    assert client.generate_calls == [
        {
            "prompt": "prompt text",
            "purpose": "semantic_extract",
        }
    ]


def test_scaffold_logger_records_context_and_attributes() -> None:
    logger = ScaffoldRecoLogger(
        context=LogContext(trace_id="trace-1", run_id="run-1"),
    )

    bound = logger.bind(run_id="run-2")
    bound.info("phase_started", phase="retrieval", top_k=10)
    logger.error("phase_failed", phase="matching", reason="scaffold")

    assert len(logger.records) == 2
    assert logger.records[0].event == "phase_started"
    assert logger.records[0].context.trace_id == "trace-1"
    assert logger.records[0].context.run_id == "run-2"
    assert logger.records[0].attributes == {"phase": "retrieval", "top_k": 10}
    assert logger.records[1].level == "error"
    assert logger.records[1].event == "phase_failed"
