"""Unit tests for api_call_log writers (E4 Wave 3)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from uuid import UUID, uuid4

import pytest

from batch.application.genre_sync.repositories import GenreSyncRepositories
from batch.application.observability import (
    PostgresApiCallLogWriter,
    ScaffoldApiCallLogWriter,
    create_api_call_log_writer,
    create_batch_observability_writers,
)
from batch.infrastructure.db import ScaffoldDbWriter
from batch.infrastructure.object_storage import ScaffoldObjectStorageClient


def test_postgres_api_call_rejects_non_uuid_ids() -> None:
    writer = ScaffoldDbWriter()
    api_writer = PostgresApiCallLogWriter(db_writer=writer)
    run_id = str(uuid4())

    with pytest.raises(ValueError, match="api_call_log_id must be a UUID"):
        api_writer.record_call(
            api_call_log_id="api_not_uuid",
            batch_run_id=run_id,
            source_api="genre_search",
            call_status="succeeded",
            request_params_json={"genre_id": "0"},
        )

    with pytest.raises(ValueError, match="batch_run_id must be a UUID"):
        api_writer.record_call(
            api_call_log_id=str(uuid4()),
            batch_run_id="local-run",
            source_api="genre_search",
            call_status="succeeded",
            request_params_json={"genre_id": "0"},
        )


def test_postgres_api_call_rejects_invalid_source_api() -> None:
    writer = ScaffoldDbWriter()
    api_writer = PostgresApiCallLogWriter(db_writer=writer)

    with pytest.raises(ValueError, match="source_api must be one of"):
        api_writer.record_call(
            api_call_log_id=str(uuid4()),
            batch_run_id=str(uuid4()),
            source_api="openai_embedding",
            call_status="succeeded",
            request_params_json={},
        )


def test_postgres_api_call_accepts_item_embedding_with_openai_source() -> None:
    writer = ScaffoldDbWriter()
    api_writer = PostgresApiCallLogWriter(db_writer=writer)
    call_id = str(uuid4())
    run_id = str(uuid4())

    api_writer.record_call(
        api_call_log_id=call_id,
        batch_run_id=run_id,
        source="openai",
        source_api="item_embedding",
        call_status="succeeded",
        request_params_json={"model": "text-embedding-3-small", "purpose": "item_embedding"},
        duration_ms=12,
    )

    row = writer.write_calls[0]["rows"][0]
    assert row["source"] == "openai"
    assert row["source_api"] == "item_embedding"
    assert row["duration_ms"] == 12
    params = row["request_params_json"]
    if hasattr(params, "obj"):
        params = params.obj
    assert params == {"model": "text-embedding-3-small", "purpose": "item_embedding"}
    assert "api_key" not in params


def test_postgres_api_call_rejects_invalid_source() -> None:
    writer = ScaffoldDbWriter()
    api_writer = PostgresApiCallLogWriter(db_writer=writer)

    with pytest.raises(ValueError, match="source must be one of"):
        api_writer.record_call(
            api_call_log_id=str(uuid4()),
            batch_run_id=str(uuid4()),
            source="amazon",
            source_api="item_embedding",
            call_status="succeeded",
            request_params_json={},
        )


def test_postgres_api_call_rejects_invalid_call_status() -> None:
    writer = ScaffoldDbWriter()
    api_writer = PostgresApiCallLogWriter(db_writer=writer)

    with pytest.raises(ValueError, match="call_status must be one of"):
        api_writer.record_call(
            api_call_log_id=str(uuid4()),
            batch_run_id=str(uuid4()),
            source_api="genre_search",
            call_status="ok",
            request_params_json={},
        )


def test_postgres_api_call_writes_expected_columns() -> None:
    writer = ScaffoldDbWriter()
    api_writer = PostgresApiCallLogWriter(db_writer=writer)
    call_id = str(uuid4())
    run_id = str(uuid4())
    params = {"genre_id": "0"}

    api_writer.record_call(
        api_call_log_id=call_id,
        batch_run_id=run_id,
        source_api="genre_search",
        call_status="succeeded",
        request_params_json=params,
        trace_id="trace-api",
    )

    assert len(writer.write_calls) == 1
    call = writer.write_calls[0]
    assert call["table"] == "api_call_log"
    row = call["rows"][0]
    assert row["api_call_log_id"] == call_id
    assert row["batch_run_id"] == run_id
    assert row["source"] == "rakuten"
    assert row["source_api"] == "genre_search"
    assert row["call_status"] == "succeeded"
    assert row["trace_id"] == "trace-api"
    assert isinstance(row["requested_at"], datetime)
    assert row["requested_at"].tzinfo is not None
    assert isinstance(row["completed_at"], datetime)
    expected_hash = hashlib.sha256(
        json.dumps(params, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    assert row["request_params_hash"] == expected_hash
    detail = row["request_params_json"]
    if hasattr(detail, "obj"):
        detail = detail.obj
    assert detail == params
    assert len(api_writer.records) == 1


def test_postgres_api_call_requested_has_null_completed_at() -> None:
    writer = ScaffoldDbWriter()
    api_writer = PostgresApiCallLogWriter(db_writer=writer)

    api_writer.record_call(
        api_call_log_id=str(uuid4()),
        batch_run_id=str(uuid4()),
        source_api="genre_search",
        call_status="requested",
        request_params_json={"genre_id": "1"},
    )

    row = writer.write_calls[0]["rows"][0]
    assert row["completed_at"] is None


def test_postgres_api_call_strips_sensitive_param_keys() -> None:
    writer = ScaffoldDbWriter()
    api_writer = PostgresApiCallLogWriter(db_writer=writer)

    api_writer.record_call(
        api_call_log_id=str(uuid4()),
        batch_run_id=str(uuid4()),
        source_api="genre_search",
        call_status="succeeded",
        request_params_json={
            "genre_id": "100",
            "Authorization": "Bearer secret",
            "api_key": "AKIA...",
            "access_key": "x",
            "token": "t",
            "password": "p",
            "secret": "s",
        },
    )

    detail = writer.write_calls[0]["rows"][0]["request_params_json"]
    if hasattr(detail, "obj"):
        detail = detail.obj
    assert detail == {"genre_id": "100"}
    assert "Authorization" not in detail
    assert "api_key" not in detail


def test_scaffold_api_call_writer_records_in_memory() -> None:
    writer = ScaffoldApiCallLogWriter()
    writer.record_call(
        api_call_log_id=str(uuid4()),
        batch_run_id="job-1",
        source_api="genre_search",
        call_status="succeeded",
        request_params_json={"genre_id": "0", "api_key": "leak"},
    )
    assert len(writer.records) == 1
    assert writer.records[0]["request_params_json"] == {"genre_id": "0"}
    assert writer.records[0]["source"] == "rakuten"


def test_create_api_call_log_writer_scaffold_paths() -> None:
    assert isinstance(
        create_api_call_log_writer(scaffold_demo=True, database_url=None),
        ScaffoldApiCallLogWriter,
    )
    assert isinstance(
        create_api_call_log_writer(scaffold_demo=False, database_url=None),
        ScaffoldApiCallLogWriter,
    )
    assert isinstance(
        create_api_call_log_writer(scaffold_demo=False, database_url=""),
        ScaffoldApiCallLogWriter,
    )
    assert isinstance(
        create_api_call_log_writer(scaffold_demo=False, database_url="scaffold://local"),
        ScaffoldApiCallLogWriter,
    )


def test_create_batch_observability_writers_includes_api_call() -> None:
    db = ScaffoldDbWriter()
    obs = create_batch_observability_writers(
        scaffold_demo=False,
        database_url="postgresql://user:pass@localhost/db",
        db_writer=db,
    )
    assert isinstance(obs.api_call_log_writer, PostgresApiCallLogWriter)


def test_genre_sync_repos_writes_api_call_log_with_uuid() -> None:
    db = ScaffoldDbWriter()
    api_writer = PostgresApiCallLogWriter(db_writer=db)
    repos = GenreSyncRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=db,
        bucket="scaffold-raw",
        api_call_log_writer=api_writer,
    )
    run_id = str(uuid4())
    call_id = str(uuid4())
    repos.bind_run(batch_run_id=run_id, trace_id="t-api")

    repos.record_api_call(
        api_call_log_id=call_id,
        genre_id="0",
        status="succeeded",
    )

    assert len(repos.api_call_logs) == 1
    UUID(repos.api_call_logs[0]["api_call_log_id"])  # type: ignore[arg-type]
    api_calls = [c for c in db.write_calls if c["table"] == "api_call_log"]
    assert len(api_calls) == 1
    row = api_calls[0]["rows"][0]
    assert row["api_call_log_id"] == call_id
    assert row["batch_run_id"] == run_id
    assert row["source_api"] == "genre_search"
    assert row["call_status"] == "succeeded"
    assert row["trace_id"] == "t-api"
    params = row["request_params_json"]
    if hasattr(params, "obj"):
        params = params.obj
    assert params == {"genre_id": "0"}


def test_genre_sync_repos_without_bind_keeps_api_call_memory_only() -> None:
    db = ScaffoldDbWriter()
    repos = GenreSyncRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=db,
        bucket="scaffold-raw",
        api_call_log_writer=PostgresApiCallLogWriter(db_writer=db),
    )
    repos.record_api_call(
        api_call_log_id=str(uuid4()),
        genre_id="0",
        status="succeeded",
    )
    assert len(repos.api_call_logs) == 1
    assert db.write_calls == []


def test_item_embedding_repos_writes_api_call_log_with_openai_source() -> None:
    from batch.application.item_embedding.repositories import ItemEmbeddingRepositories

    db = ScaffoldDbWriter()
    api_writer = PostgresApiCallLogWriter(db_writer=db)
    repos = ItemEmbeddingRepositories(
        db_writer=db,
        api_call_log_writer=api_writer,
    )
    run_id = str(uuid4())
    call_id = str(uuid4())
    repos.bind_run(batch_run_id=run_id, trace_id="t-emb")

    repos.record_api_call(
        api_call_log_id=call_id,
        status="generated",
        model="text-embedding-3-small",
        latency_ms=42,
    )

    assert len(repos.api_call_logs) == 1
    mem = repos.api_call_logs[0]
    assert mem["api_call_log_id"] == call_id
    assert mem["status"] == "generated"
    assert mem["call_status"] == "succeeded"
    assert mem["model"] == "text-embedding-3-small"
    assert "embedding_vector" not in mem
    assert "api_key" not in str(mem).lower()

    api_calls = [c for c in db.write_calls if c["table"] == "api_call_log"]
    assert len(api_calls) == 1
    row = api_calls[0]["rows"][0]
    assert row["api_call_log_id"] == call_id
    assert row["batch_run_id"] == run_id
    assert row["source"] == "openai"
    assert row["source_api"] == "item_embedding"
    assert row["call_status"] == "succeeded"
    assert row["duration_ms"] == 42
    assert row["trace_id"] == "t-emb"
    params = row["request_params_json"]
    if hasattr(params, "obj"):
        params = params.obj
    assert params == {"model": "text-embedding-3-small", "purpose": "item_embedding"}
    assert "api_key" not in params


def test_item_embedding_repos_without_bind_keeps_api_call_memory_only() -> None:
    from batch.application.item_embedding.repositories import ItemEmbeddingRepositories

    db = ScaffoldDbWriter()
    repos = ItemEmbeddingRepositories(
        db_writer=db,
        api_call_log_writer=PostgresApiCallLogWriter(db_writer=db),
    )
    repos.record_api_call(
        api_call_log_id=str(uuid4()),
        status="generated",
        model="scaffold-model",
        latency_ms=1,
    )
    assert len(repos.api_call_logs) == 1
    assert db.write_calls == []


def test_rakuten_path_default_source_unchanged() -> None:
    """001〜004 経路の既定 source=rakuten が回帰しないこと。"""

    writer = ScaffoldDbWriter()
    api_writer = PostgresApiCallLogWriter(db_writer=writer)
    api_writer.record_call(
        api_call_log_id=str(uuid4()),
        batch_run_id=str(uuid4()),
        source_api="genre_search",
        call_status="succeeded",
        request_params_json={"genre_id": "0"},
    )
    assert writer.write_calls[0]["rows"][0]["source"] == "rakuten"