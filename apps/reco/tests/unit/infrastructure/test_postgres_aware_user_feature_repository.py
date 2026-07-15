"""Unit tests for PostgresAwareUserFeatureRepository."""

from __future__ import annotations

from datetime import UTC, datetime

from reco.application.user_feature_generator.models import UserFeatureInsertRow
from reco.infrastructure.db.repositories.postgres_aware_user_feature_repository import (
    PostgresAwareUserFeatureRepository,
)
from unit.infrastructure.db.helpers import ScriptedDatabaseSession


def test_has_user_semantic_reads_postgres() -> None:
    session = ScriptedDatabaseSession(scripted_query_results=[[{"found": 1}]])
    repo = PostgresAwareUserFeatureRepository(session=session)
    assert repo.has_user_semantic("run-1") is True


def test_has_user_semantic_false_when_missing() -> None:
    session = ScriptedDatabaseSession(scripted_query_results=[[]])
    repo = PostgresAwareUserFeatureRepository(session=session)
    assert repo.has_user_semantic("run-missing") is False


def test_insert_user_features_keeps_memory_rows() -> None:
    session = ScriptedDatabaseSession()
    repo = PostgresAwareUserFeatureRepository(session=session)
    row = UserFeatureInsertRow(
        recommendation_run_id="run-1",
        feature_code="formality",
        feature_normalization_version_id="norm-1",
        feature_value=0.5,
        source_type="aggregated",
        generated_at=datetime.now(UTC),
    )
    repo.insert_user_features((row,))
    assert repo.inserted_rows == [row]
