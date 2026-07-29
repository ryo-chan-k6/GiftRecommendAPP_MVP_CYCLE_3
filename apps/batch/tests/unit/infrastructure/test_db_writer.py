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
    resolve_job_db_writer,
)


def test_scaffold_db_writer_records_writes() -> None:
    writer = ScaffoldDbWriter()
    rows = ({"item_code": "item-1"}, {"item_code": "item-2"})

    result = writer.write_rows("items", rows)

    assert result == DbWriteResult(rows_affected=2, table="items")
    assert writer.write_calls == [{"table": "items", "rows": rows}]


def test_scaffold_db_writer_records_upserts() -> None:
    writer = ScaffoldDbWriter()
    rows = ({"batch_run_id": "r1", "external_item_code": "shop:a", "diff_status": "new"},)

    result = writer.upsert_rows(
        "product_diff_result",
        rows,
        conflict_columns=("batch_run_id", "external_item_code"),
        update_columns=("diff_status",),
    )

    assert result == DbWriteResult(rows_affected=1, table="product_diff_result")
    assert writer.upsert_calls == [
        {
            "table": "product_diff_result",
            "rows": rows,
            "conflict_columns": ("batch_run_id", "external_item_code"),
            "update_columns": ("diff_status",),
            "conflict_where": None,
        }
    ]


def test_resolve_job_db_writer_scaffold_demo_ignores_url() -> None:
    writer = resolve_job_db_writer(
        scaffold_demo=True,
        database_url="postgresql://localhost:5432/gift",
    )
    assert isinstance(writer, ScaffoldDbWriter)


def test_resolve_job_db_writer_uses_create_db_writer() -> None:
    writer = resolve_job_db_writer(
        scaffold_demo=False,
        database_url="postgresql://localhost:5432/gift",
    )
    assert isinstance(writer, PostgresDbWriter)


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


def test_postgres_write_rows_adapts_dict_to_json() -> None:
    """fetch_cursor.scope 等の dict を jsonb 向け Json に変換する（live INSERT 失敗回避）。"""

    from psycopg.types.json import Json

    writer = PostgresDbWriter(database_url="postgresql://localhost:5432/gift")
    rows = ({"fetch_cursor_id": "fc_1", "scope": {"genre_id": "100"}},)

    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = False

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = False

    with patch("psycopg.connect", return_value=mock_conn):
        writer.write_rows("fetch_cursor", rows)

    _statement, params = mock_cursor.execute.call_args.args
    assert params[0] == "fc_1"
    assert isinstance(params[1], Json)
    assert params[1].obj == {"genre_id": "100"}


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


def test_scaffold_db_writer_records_updates() -> None:
    writer = ScaffoldDbWriter()
    result = writer.update_rows(
        "raw_product_metadata",
        set_values={"import_status": "staged", "staged_at": "2026-07-27T00:00:00Z"},
        equals=(("raw_metadata_id", "rm-1"),),
    )

    assert result == DbWriteResult(rows_affected=1, table="raw_product_metadata")
    assert writer.update_calls == [
        {
            "table": "raw_product_metadata",
            "set_values": {
                "import_status": "staged",
                "staged_at": "2026-07-27T00:00:00Z",
            },
            "equals": (("raw_metadata_id", "rm-1"),),
        }
    ]


def test_scaffold_db_writer_records_deletes() -> None:
    writer = ScaffoldDbWriter()
    result = writer.delete_rows(
        "staging_item_image",
        equals=(
            ("raw_metadata_id", "rm-1"),
            ("external_item_code", "shop:a"),
            ("image_url", "https://img.example/x.jpg"),
        ),
    )

    assert result == DbWriteResult(rows_affected=1, table="staging_item_image")
    assert writer.delete_calls == [
        {
            "table": "staging_item_image",
            "equals": (
                ("raw_metadata_id", "rm-1"),
                ("external_item_code", "shop:a"),
                ("image_url", "https://img.example/x.jpg"),
            ),
        }
    ]


def test_postgres_update_rows_rejects_empty_equals() -> None:
    writer = PostgresDbWriter(database_url="postgresql://localhost:5432/gift")
    with pytest.raises(DatabaseError, match="equals"):
        writer.update_rows(
            "raw_product_metadata",
            set_values={"import_status": "failed"},
            equals=(),
        )


def test_postgres_delete_rows_rejects_empty_equals() -> None:
    writer = PostgresDbWriter(database_url="postgresql://localhost:5432/gift")
    with pytest.raises(DatabaseError, match="equals"):
        writer.delete_rows("staging_item_image", equals=())


def test_postgres_update_rows_executes_parameterized_update() -> None:
    writer = PostgresDbWriter(database_url="postgresql://localhost:5432/gift")

    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = False

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = False

    with patch("psycopg.connect", return_value=mock_conn) as connect:
        result = writer.update_rows(
            "raw_product_metadata",
            set_values={
                "import_status": "failed",
                "error_code": "GRS-RAW-005",
                "error_message": "staging failed: GRS-RAW-005",
            },
            equals=(("raw_metadata_id", "rm-1"),),
        )

    connect.assert_called_once_with("postgresql://localhost:5432/gift")
    mock_cursor.execute.assert_called_once()
    _statement, params = mock_cursor.execute.call_args.args
    assert params == [
        "failed",
        "GRS-RAW-005",
        "staging failed: GRS-RAW-005",
        "rm-1",
    ]
    mock_conn.commit.assert_called_once()
    assert result == DbWriteResult(rows_affected=1, table="raw_product_metadata")


def test_postgres_delete_rows_executes_parameterized_delete() -> None:
    writer = PostgresDbWriter(database_url="postgresql://localhost:5432/gift")

    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = False

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = False

    with patch("psycopg.connect", return_value=mock_conn) as connect:
        result = writer.delete_rows(
            "staging_item_image",
            equals=(
                ("raw_metadata_id", "rm-1"),
                ("external_item_code", "shop:a"),
                ("image_url", "https://img.example/x.jpg"),
            ),
        )

    connect.assert_called_once_with("postgresql://localhost:5432/gift")
    mock_cursor.execute.assert_called_once()
    _statement, params = mock_cursor.execute.call_args.args
    assert params == ["rm-1", "shop:a", "https://img.example/x.jpg"]
    mock_conn.commit.assert_called_once()
    assert result == DbWriteResult(rows_affected=1, table="staging_item_image")


def test_postgres_update_rows_rejects_invalid_table() -> None:
    writer = PostgresDbWriter(database_url="postgresql://localhost:5432/gift")
    with pytest.raises(DatabaseError, match="invalid SQL table"):
        writer.update_rows(
            "raw;drop",
            set_values={"import_status": "staged"},
            equals=(("raw_metadata_id", "rm-1"),),
        )


def test_postgres_upsert_rows_rejects_empty_conflict() -> None:
    writer = PostgresDbWriter(database_url="postgresql://localhost:5432/gift")
    with pytest.raises(DatabaseError, match="conflict_columns"):
        writer.upsert_rows(
            "product_diff_result",
            ({"batch_run_id": "r1", "external_item_code": "a"},),
            conflict_columns=(),
        )


def test_postgres_upsert_rows_executes_on_conflict() -> None:
    writer = PostgresDbWriter(database_url="postgresql://localhost:5432/gift")
    rows = (
        {
            "batch_run_id": "r1",
            "external_item_code": "shop:a",
            "diff_status": "new",
        },
    )

    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = False

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = False

    with patch("psycopg.connect", return_value=mock_conn) as connect:
        result = writer.upsert_rows(
            "product_diff_result",
            rows,
            conflict_columns=("batch_run_id", "external_item_code"),
            update_columns=("diff_status",),
        )

    connect.assert_called_once_with("postgresql://localhost:5432/gift")
    mock_cursor.execute.assert_called_once()
    _statement, params = mock_cursor.execute.call_args.args
    assert params == ["r1", "shop:a", "new"]
    mock_conn.commit.assert_called_once()
    assert result == DbWriteResult(rows_affected=1, table="product_diff_result")


def _flatten_sql(fragment: object) -> str:
    """Render psycopg.sql fragments for statement shape assertions."""

    from psycopg import sql

    if isinstance(fragment, sql.Composed):
        return "".join(_flatten_sql(part) for part in fragment)
    if isinstance(fragment, sql.SQL):
        return str(fragment._obj)  # noqa: SLF001 — test-only render
    if isinstance(fragment, sql.Identifier):
        return ".".join(str(part) for part in fragment._obj)  # noqa: SLF001
    if isinstance(fragment, sql.Placeholder):
        return "%s"
    return str(fragment)


def test_scaffold_upsert_records_conflict_where() -> None:
    writer = ScaffoldDbWriter()
    rows = (
        {
            "aggregation_scope": "daily",
            "aggregation_key": "2026-07-21",
            "semantic_config_version_id": "v1",
            "feature_code": "formality",
            "value_layer": "raw",
            "sample_count": 2,
        },
    )

    result = writer.upsert_rows(
        "feature_distribution_metric",
        rows,
        conflict_columns=(
            "aggregation_scope",
            "aggregation_key",
            "semantic_config_version_id",
            "feature_code",
            "value_layer",
        ),
        update_columns=("sample_count",),
        conflict_where=(("aggregation_scope", "<>", "batch_run"),),
    )

    assert result.rows_affected == 1
    assert writer.upsert_calls[0]["conflict_where"] == (
        ("aggregation_scope", "<>", "batch_run"),
    )


def test_scaffold_transaction_records_calls() -> None:
    writer = ScaffoldDbWriter()
    with writer.transaction():
        writer.update_rows(
            "item_feature",
            set_values={"normalized_feature_value": 0.5},
            equals=(("item_id", "it_1"),),
        )
        writer.upsert_rows(
            "item_meaning",
            ({"item_id": "it_1", "semantic_config_version_id": "v1"},),
            conflict_columns=("item_id", "semantic_config_version_id"),
        )

    assert len(writer.transaction_calls) == 1
    assert len(writer.update_calls) == 1
    assert len(writer.upsert_calls) == 1


def test_postgres_upsert_rows_includes_conflict_where_in_sql() -> None:
    writer = PostgresDbWriter(database_url="postgresql://localhost:5432/gift")
    rows = (
        {
            "aggregation_scope": "daily",
            "aggregation_key": "2026-07-21",
            "semantic_config_version_id": "v1",
            "feature_code": "formality",
            "value_layer": "raw",
            "sample_count": 2,
        },
    )

    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = False

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = False

    with patch("psycopg.connect", return_value=mock_conn):
        writer.upsert_rows(
            "feature_distribution_metric",
            rows,
            conflict_columns=(
                "aggregation_scope",
                "aggregation_key",
                "semantic_config_version_id",
                "feature_code",
                "value_layer",
            ),
            update_columns=("sample_count",),
            conflict_where=(("aggregation_scope", "<>", "batch_run"),),
        )

    statement, params = mock_cursor.execute.call_args.args
    rendered = _flatten_sql(statement)
    assert "ON CONFLICT" in rendered
    assert "WHERE" in rendered
    assert "<>" in rendered
    assert params[-1] == "batch_run"
    assert params[:6] == ["daily", "2026-07-21", "v1", "formality", "raw", 2]


def test_postgres_upsert_rejects_invalid_conflict_where_operator() -> None:
    writer = PostgresDbWriter(database_url="postgresql://localhost:5432/gift")
    with pytest.raises(DatabaseError, match="unsupported conflict_where operator"):
        writer.upsert_rows(
            "feature_distribution_metric",
            (
                {
                    "aggregation_scope": "daily",
                    "aggregation_key": "2026-07-21",
                    "semantic_config_version_id": "v1",
                    "feature_code": "formality",
                    "value_layer": "raw",
                },
            ),
            conflict_columns=(
                "aggregation_scope",
                "aggregation_key",
                "semantic_config_version_id",
                "feature_code",
                "value_layer",
            ),
            conflict_where=(("aggregation_scope", "!=", "batch_run"),),  # type: ignore[arg-type]
        )


def test_postgres_transaction_commits_once_for_multiple_dml() -> None:
    writer = PostgresDbWriter(database_url="postgresql://localhost:5432/gift")

    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = False

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("psycopg.connect", return_value=mock_conn) as connect:
        with writer.transaction():
            writer.update_rows(
                "item_feature",
                set_values={"normalized_feature_value": 0.5},
                equals=(
                    ("item_id", "it_1"),
                    ("semantic_config_version_id", "v1"),
                    ("feature_code", "formality"),
                    ("feature_input_hash", "h1"),
                    ("feature_normalization_version_id", "n1"),
                ),
            )
            writer.upsert_rows(
                "item_meaning",
                (
                    {
                        "item_id": "it_1",
                        "semantic_config_version_id": "v1",
                        "feature_normalization_version_id": "n1",
                        "item_social": 0.4,
                        "item_symbolic": 0.6,
                        "generated_at": "2026-07-28T00:00:00Z",
                    },
                ),
                conflict_columns=("item_id", "semantic_config_version_id"),
                update_columns=(
                    "feature_normalization_version_id",
                    "item_social",
                    "item_symbolic",
                    "generated_at",
                ),
            )

    connect.assert_called_once_with("postgresql://localhost:5432/gift")
    assert mock_cursor.execute.call_count == 2
    mock_conn.commit.assert_called_once()
    mock_conn.rollback.assert_not_called()
    mock_conn.close.assert_called_once()


def test_postgres_transaction_rolls_back_on_error() -> None:
    writer = PostgresDbWriter(database_url="postgresql://localhost:5432/gift")

    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = False
    mock_cursor.execute.side_effect = [None, RuntimeError("boom")]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("psycopg.connect", return_value=mock_conn):
        with pytest.raises(DatabaseError, match="boom"):
            with writer.transaction():
                writer.update_rows(
                    "item_feature",
                    set_values={"normalized_feature_value": 0.5},
                    equals=(("item_id", "it_1"),),
                )
                writer.update_rows(
                    "item_feature",
                    set_values={"normalized_feature_value": 0.6},
                    equals=(("item_id", "it_2"),),
                )

    mock_conn.commit.assert_not_called()
    mock_conn.rollback.assert_called_once()
    mock_conn.close.assert_called_once()
