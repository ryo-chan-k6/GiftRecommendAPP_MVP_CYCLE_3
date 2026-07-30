"""Unit tests for DbReader foundation (Scaffold / Postgres factory)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from batch.infrastructure.db import (
    DatabaseError,
    DbReadResult,
    PostgresDbReader,
    ScaffoldDbReader,
    create_db_reader,
    is_live_db_reader,
    resolve_job_db_reader,
)


def test_scaffold_db_reader_filters_projects_and_limits() -> None:
    reader = ScaffoldDbReader()
    reader.seed(
        "raw_product_metadata",
        (
            {"id": 1, "status": "pending", "path": "a"},
            {"id": 2, "status": "done", "path": "b"},
            {"id": 3, "status": "pending", "path": "c"},
        ),
    )

    result = reader.fetch_rows(
        "raw_product_metadata",
        columns=("id", "path"),
        equals=(("status", "pending"),),
        order_by=("id",),
        limit=1,
    )

    assert result == DbReadResult(rows=({"id": 1, "path": "a"},), table="raw_product_metadata")
    assert result.row_count == 1
    assert reader.fetch_calls[0]["table"] == "raw_product_metadata"


def test_resolve_job_db_reader_scaffold_demo_ignores_url() -> None:
    reader = resolve_job_db_reader(
        scaffold_demo=True,
        database_url="postgresql://localhost:5432/gift",
    )
    assert isinstance(reader, ScaffoldDbReader)
    assert not is_live_db_reader(reader)


def test_resolve_job_db_reader_uses_create_db_reader() -> None:
    reader = resolve_job_db_reader(
        scaffold_demo=False,
        database_url="postgresql://localhost:5432/gift",
    )
    assert isinstance(reader, PostgresDbReader)
    assert is_live_db_reader(reader)


def test_create_db_reader_uses_scaffold_for_missing_url() -> None:
    assert isinstance(create_db_reader(None), ScaffoldDbReader)


def test_create_db_reader_uses_scaffold_for_empty_url() -> None:
    assert isinstance(create_db_reader(""), ScaffoldDbReader)


def test_create_db_reader_uses_scaffold_for_scaffold_url() -> None:
    assert isinstance(create_db_reader("scaffold://database"), ScaffoldDbReader)


def test_create_db_reader_uses_postgres_for_real_url() -> None:
    reader = create_db_reader("postgresql://localhost:5432/gift_batch_dev")
    assert isinstance(reader, PostgresDbReader)
    assert reader.backend == "postgres"


def test_create_db_reader_respects_fallback() -> None:
    fallback = ScaffoldDbReader()
    assert create_db_reader(None, fallback=fallback) is fallback


def test_postgres_fetch_rows_rejects_invalid_table() -> None:
    reader = PostgresDbReader(database_url="postgresql://localhost:5432/gift")
    with pytest.raises(DatabaseError, match="invalid SQL table"):
        reader.fetch_rows("items;drop", columns=("id",))


def test_postgres_fetch_rows_rejects_empty_columns() -> None:
    reader = PostgresDbReader(database_url="postgresql://localhost:5432/gift")
    with pytest.raises(DatabaseError, match="columns require"):
        reader.fetch_rows("items", columns=())


def test_postgres_fetch_rows_rejects_invalid_limit() -> None:
    reader = PostgresDbReader(database_url="postgresql://localhost:5432/gift")
    with pytest.raises(DatabaseError, match="limit must be a positive int"):
        reader.fetch_rows("items", columns=("id",), limit=0)


def test_postgres_fetch_rows_executes_parameterized_select() -> None:
    reader = PostgresDbReader(database_url="postgresql://localhost:5432/gift")

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [{"id": 1, "path": "a"}]
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = False

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = False

    with patch("psycopg.connect", return_value=mock_conn) as connect:
        result = reader.fetch_rows(
            "raw_product_metadata",
            columns=("id", "path"),
            equals=(("status", "pending"),),
            order_by=("id",),
            limit=10,
        )

    connect.assert_called_once()
    assert connect.call_args.args[0] == "postgresql://localhost:5432/gift"
    mock_cursor.execute.assert_called_once()
    _statement, params = mock_cursor.execute.call_args.args
    assert params == ["pending"]
    assert result == DbReadResult(rows=({"id": 1, "path": "a"},), table="raw_product_metadata")


def test_scaffold_db_reader_filters_bool_and_uuid_equals() -> None:
    """current version 解決で使う bool / UUID equals が値一致で絞り込まれる。"""

    version_id = "a1111111-1111-4111-8111-111111111102"
    reader = ScaffoldDbReader()
    reader.seed(
        "normalization_rule",
        (
            {
                "normalization_rule_id": "b2222222-2222-4222-8222-222222222202",
                "semantic_config_version_id": version_id,
                "is_active": True,
            },
            {
                "normalization_rule_id": "b2222222-2222-4222-8222-222222222203",
                "semantic_config_version_id": version_id,
                "is_active": False,
            },
            {
                "normalization_rule_id": "b2222222-2222-4222-8222-222222222204",
                "semantic_config_version_id": "a1111111-1111-4111-8111-111111111199",
                "is_active": True,
            },
        ),
    )

    result = reader.fetch_rows(
        "normalization_rule",
        columns=("normalization_rule_id",),
        equals=(("semantic_config_version_id", version_id), ("is_active", True)),
        limit=2,
    )

    assert result.rows == ({"normalization_rule_id": "b2222222-2222-4222-8222-222222222202"},)


def test_postgres_fetch_rows_binds_bool_and_uuid_equals_as_parameters() -> None:
    """bool / UUID の equals は SQL 文へ埋め込まず parameter binding する。"""

    version_id = "a1111111-1111-4111-8111-111111111102"
    reader = PostgresDbReader(database_url="postgresql://localhost:5432/gift")

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [{"normalization_rule_id": "rule-1"}]
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = False

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = False

    with patch("psycopg.connect", return_value=mock_conn):
        reader.fetch_rows(
            "normalization_rule",
            columns=("normalization_rule_id",),
            equals=(("semantic_config_version_id", version_id), ("is_active", True)),
            limit=2,
        )

    statement, params = mock_cursor.execute.call_args.args
    assert params == [version_id, True]
    rendered = statement.as_string(None)
    assert rendered.count("%s") == 2
    assert version_id not in rendered
    assert "true" not in rendered.lower()


def test_postgres_fetch_rows_masks_credentials_in_database_error() -> None:
    reader = PostgresDbReader(
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
        reader.fetch_rows("staging_item", columns=("item_code",))

    message = str(exc_info.value)
    assert "secret" not in message
    assert "***REDACTED***" in message
    assert "localhost:5432/gift" in message
