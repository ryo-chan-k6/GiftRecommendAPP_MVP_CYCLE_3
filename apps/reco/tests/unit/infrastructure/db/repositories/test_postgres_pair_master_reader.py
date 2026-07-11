"""PostgresPairMasterReader unit tests."""

from __future__ import annotations

from uuid import uuid4

from reco.infrastructure.db.repositories.pair_master_reader import (
    InMemoryPairMasterReader,
    PostgresPairMasterReader,
)
from unit.infrastructure.db.helpers import ScriptedDatabaseSession


def test_postgres_pair_master_reader_resolves_active_pair() -> None:
    pair_id = str(uuid4())
    session = ScriptedDatabaseSession(
        scripted_query_results=[[{"pair_id": pair_id}]],
    )
    reader = PostgresPairMasterReader(session=session)

    resolved = reader.resolve_pair_id(
        relationship_code="boss",
        occasion_code="thanks",
    )

    assert resolved == pair_id
    assert session.operations[0][0] == "query"
    sql = session.operations[0][1]
    assert "pair_master" in sql
    assert "is_active = true" in sql
    assert session.operations[0][2] == ("boss", "thanks")


def test_postgres_pair_master_reader_ignores_inactive_pair() -> None:
    """is_active=false 相当（行なし）では None を返す。"""
    session = ScriptedDatabaseSession(scripted_query_results=[[]])
    reader = PostgresPairMasterReader(session=session)

    assert (
        reader.resolve_pair_id(
            relationship_code="boss",
            occasion_code="thanks",
        )
        is None
    )
    assert "is_active = true" in session.operations[0][1]


def test_postgres_pair_master_reader_returns_none_when_missing() -> None:
    session = ScriptedDatabaseSession(scripted_query_results=[[]])
    reader = PostgresPairMasterReader(session=session)

    assert (
        reader.resolve_pair_id(
            relationship_code="friend",
            occasion_code="birthday",
        )
        is None
    )


def test_in_memory_pair_master_reader_still_resolves_scaffold_key() -> None:
    reader = InMemoryPairMasterReader(
        pairs={("friend", "birthday"): "pair-scaffold-friend-birthday"},
    )

    assert (
        reader.resolve_pair_id(
            relationship_code="friend",
            occasion_code="birthday",
        )
        == "pair-scaffold-friend-birthday"
    )
    assert (
        reader.resolve_pair_id(
            relationship_code="boss",
            occasion_code="thanks",
        )
        is None
    )
