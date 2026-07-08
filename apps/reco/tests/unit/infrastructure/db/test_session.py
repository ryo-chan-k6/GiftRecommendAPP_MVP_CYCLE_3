"""Database session unit tests."""

from __future__ import annotations

import pytest

from reco.infrastructure.db.session import (
    DatabaseError,
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


def test_scaffold_session_records_operations() -> None:
    session = ScaffoldDatabaseSession(query_rows=[{"ok": 1}], affected_rows=2)

    assert session.query("SELECT 1", ()) == [{"ok": 1}]
    assert session.execute("UPDATE t SET x = 1", (1,)) == 2
    assert len(session.operations) == 2


def test_scaffold_session_raises_when_unavailable() -> None:
    session = ScaffoldDatabaseSession(is_available=False)

    with pytest.raises(DatabaseError, match="unavailable"):
        session.query("SELECT 1")
