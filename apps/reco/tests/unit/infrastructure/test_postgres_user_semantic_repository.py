"""Unit tests for PostgresUserSemanticRepository."""

from __future__ import annotations

from datetime import UTC, datetime

from reco.infrastructure.db.repositories.postgres_user_semantic_repository import (
    PostgresUserSemanticRepository,
)
from unit.infrastructure.db.helpers import ScriptedDatabaseSession


def test_exists_for_run_true_when_row_present() -> None:
    session = ScriptedDatabaseSession(
        scripted_query_results=[[{"found": 1}]],
    )
    repo = PostgresUserSemanticRepository(session=session)
    assert repo.exists_for_run("run-1") is True


def test_exists_for_run_false_when_missing() -> None:
    session = ScriptedDatabaseSession(scripted_query_results=[[]])
    repo = PostgresUserSemanticRepository(session=session)
    assert repo.exists_for_run("run-missing") is False


def test_insert_returns_user_semantic_record() -> None:
    run_id = "11111111-1111-4111-8111-111111111111"
    version_id = "22222222-2222-4222-8222-222222222222"
    semantic_id = "33333333-3333-4333-8333-333333333333"
    generated_at = datetime.now(UTC)
    payload = {"concepts": []}
    session = ScriptedDatabaseSession(
        scripted_query_results=[
            [
                {
                    "user_semantic_id": semantic_id,
                    "recommendation_run_id": run_id,
                    "semantic_config_version_id": version_id,
                    "extracted_semantic_json": payload,
                    "generated_at": generated_at,
                },
            ],
        ],
    )
    repo = PostgresUserSemanticRepository(session=session)

    record = repo.insert(
        recommendation_run_id=run_id,
        semantic_config_version_id=version_id,
        extracted_semantic_json=payload,
    )

    assert record.user_semantic_id == semantic_id
    assert record.recommendation_run_id == run_id
    assert record.semantic_config_version_id == version_id
    assert record.extracted_semantic_json == payload
    assert record.generated_at == generated_at
    assert session.operations
    assert session.operations[0][0] == "query"
