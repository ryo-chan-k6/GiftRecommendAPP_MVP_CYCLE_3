"""Database session unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from reco.infrastructure.db.session import (
    DEFAULT_POOL_MAX_SIZE,
    DEFAULT_POOL_MIN_SIZE,
    DatabaseError,
    PostgresDatabaseSession,
    ScaffoldDatabaseSession,
    create_database_session,
    mask_database_url,
)


def test_mask_database_url_redacts_credentials() -> None:
    masked = mask_database_url("postgresql://user:secret@localhost:5432/gift_reco_dev")
    assert "secret" not in masked
    assert "user" not in masked
    assert "localhost:5432/gift_reco_dev" in masked


def test_create_database_session_uses_scaffold_for_missing_url() -> None:
    session = create_database_session(None)
    assert session.backend == "scaffold"


def test_create_database_session_uses_scaffold_for_scaffold_url() -> None:
    session = create_database_session("scaffold://database")
    assert session.backend == "scaffold"


def test_create_database_session_uses_postgres_for_real_url() -> None:
    session = create_database_session("postgresql://localhost:5432/gift_reco_dev")
    assert session.backend == "postgres"
    assert isinstance(session, PostgresDatabaseSession)
    assert session.min_size == DEFAULT_POOL_MIN_SIZE
    assert session.max_size == DEFAULT_POOL_MAX_SIZE
    # コンストラクタでは接続しない（open=False）
    assert session._opened is False
    session.close()


def test_postgres_session_rejects_empty_url() -> None:
    with pytest.raises(DatabaseError, match="empty"):
        PostgresDatabaseSession(database_url="   ")


def test_postgres_session_rejects_invalid_pool_size() -> None:
    with pytest.raises(DatabaseError, match="invalid pool size"):
        PostgresDatabaseSession(
            database_url="postgresql://localhost:5432/gift_reco_dev",
            min_size=3,
            max_size=2,
        )


def test_postgres_session_query_uses_injected_pool() -> None:
    pool = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = [{"ok": 1}]
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = None
    conn.cursor.return_value = cursor
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = None
    pool.connection.return_value = conn

    session = PostgresDatabaseSession(
        database_url="postgresql://localhost:5432/gift_reco_dev",
        pool=pool,
    )
    rows = session.query("SELECT 1 AS ok")
    assert rows == [{"ok": 1}]
    pool.connection.assert_called_once()
    session.close()
    pool.close.assert_not_called()


def test_postgres_session_query_wraps_pool_error() -> None:
    pool = MagicMock()
    pool.connection.side_effect = RuntimeError("connection failed")
    session = PostgresDatabaseSession(
        database_url="postgresql://localhost:5432/gift_reco_dev",
        pool=pool,
    )

    with pytest.raises(DatabaseError, match="connection failed"):
        session.query("SELECT 1")


def test_postgres_session_execute_commits_via_injected_pool() -> None:
    pool = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    cursor.rowcount = 3
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = None
    conn.cursor.return_value = cursor
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = None
    pool.connection.return_value = conn

    session = PostgresDatabaseSession(
        database_url="postgresql://localhost:5432/gift_reco_dev",
        pool=pool,
    )
    assert session.execute("UPDATE t SET x = 1") == 3
    conn.commit.assert_called_once()
    session.close()


def test_scaffold_session_records_operations() -> None:
    session = ScaffoldDatabaseSession(query_rows=[{"ok": 1}], affected_rows=2)

    assert session.query("SELECT 1", ()) == [{"ok": 1}]
    assert session.execute("UPDATE t SET x = 1", (1,)) == 2
    assert len(session.operations) == 2


def test_scaffold_session_raises_when_unavailable() -> None:
    session = ScaffoldDatabaseSession(is_available=False)

    with pytest.raises(DatabaseError, match="unavailable"):
        session.query("SELECT 1")
