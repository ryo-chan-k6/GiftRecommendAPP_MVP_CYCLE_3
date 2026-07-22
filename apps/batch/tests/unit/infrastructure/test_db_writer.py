"""Unit tests for DbWriter foundation (Scaffold / Postgres factory)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from batch.infrastructure.db import (
    DatabaseError,
    DbWriteResult,
    PostgresDbWriter,
    ScaffoldDbWriter,
    create_db_writer,
    mask_database_url,
)


def test_scaffold_db_writer_records_writes() -> None:
    writer = ScaffoldDbWriter()
    rows = ({"item_code": "item-1"}, {"item_code": "item-2"})

    result = writer.write_rows("items", rows)

    assert result == DbWriteResult(rows_affected=2, table="items")
    assert writer.write_calls == [{"table": "items", "rows": rows}]


def test_create_db_writer_uses_scaffold_for_missing_url() -> None:
    writer = create_db_writer(None)
    assert isinstance(writer, ScaffoldDbWriter)


def test_create_db_writer_uses_scaffold_for_empty_url() -> None:
    writer = create_db_writer("")
    assert isinstance(writer, ScaffoldDbWriter)


def test_create_db_writer_uses_scaffold_for_scaffold_url() -> None:
    writer = create_db_writer("scaffold://database")
    assert isinstance(writer, ScaffoldDbWriter)


def test_create_db_writer_uses_postgres_for_real_url() -> None:
    writer = create_db_writer("postgresql://localhost:5432/gift_batch_dev")
    assert isinstance(writer, PostgresDbWriter)
    assert writer.backend == "postgres"


def test_create_db_writer_respects_fallback() -> None:
    fallback = ScaffoldDbWriter()
    writer = create_db_writer(None, fallback=fallback)
    assert writer is fallback


def test_mask_database_url_redacts_credentials() -> None:
    masked = mask_database_url("postgresql://user:secret@localhost:5432/gift")
    assert "secret" not in masked
    assert "***REDACTED***" in masked
    assert "localhost:5432/gift" in masked


def test_postgres_write_rows_rejects_invalid_table() -> None:
    writer = PostgresDbWriter(database_url="postgresql://localhost:5432/gift")
    with pytest.raises(DatabaseError, match="invalid SQL table"):
        writer.write_rows("items;drop", ({"a": 1},))


def test_postgres_write_rows_empty_is_noop() -> None:
    writer = PostgresDbWriter(database_url="postgresql://localhost:5432/gift")
    result = writer.write_rows("items", ())
    assert result == DbWriteResult(rows_affected=0, table="items")


def test_postgres_write_rows_executes_parameterized_insert() -> None:
    writer = PostgresDbWriter(database_url="postgresql://localhost:5432/gift")
    rows = ({"item_code": "a", "name": "n1"}, {"item_code": "b", "name": "n2"})

    mock_cursor = MagicMock()
    mock_cursor.rowcount = 2
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = False

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = False

    with patch("psycopg.connect", return_value=mock_conn) as connect:
        result = writer.write_rows("staging_item", rows)

    connect.assert_called_once_with("postgresql://localhost:5432/gift")
    mock_cursor.execute.assert_called_once()
    _statement, params = mock_cursor.execute.call_args.args
    assert params == ["a", "n1", "b", "n2"]
    mock_conn.commit.assert_called_once()
    assert result == DbWriteResult(rows_affected=2, table="staging_item")


def test_postgres_write_rows_masks_credentials_in_database_error() -> None:
    writer = PostgresDbWriter(
        database_url="postgresql://user:secret@localhost:5432/gift"
    )

    with (
        patch(
            "psycopg.connect",
            side_effect=RuntimeError(
                "connection failed: postgresql://user:secret@localhost:5432/gift"
            ),
        ),
        pytest.raises(DatabaseError) as exc_info,
    ):
        writer.write_rows("staging_item", ({"item_code": "a"},))

    message = str(exc_info.value)
    assert "secret" not in message
    assert "***REDACTED***" in message
    assert "localhost:5432/gift" in message
