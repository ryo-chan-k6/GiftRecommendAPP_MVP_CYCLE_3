"""PostgresConfigRepository unit tests."""

from __future__ import annotations

from uuid import uuid4

from reco.application.config_version_resolver import (
    PostgresConfigRepository,
    ProductionConfigRepository,
    build_production_config_repository,
)
from unit.infrastructure.db.helpers import ScriptedDatabaseSession


def test_postgres_config_repository_reads_current_model_and_configs() -> None:
    embedding_id = str(uuid4())
    ranking_id = str(uuid4())
    matching_id = str(uuid4())
    session = ScriptedDatabaseSession(
        scripted_query_results=[
            [{"model_version_id": embedding_id, "model_type": "embedding", "is_current": True}],
            [{"ranking_config_id": ranking_id, "config_name": "mvp_ranking_config", "is_current": True}],
            [
                {
                    "matching_config_id": matching_id,
                    "config_name": "mvp_matching_config",
                    "is_current": True,
                    "parameter_json": {"distance_method": "absolute_distance"},
                }
            ],
        ]
    )
    repository = PostgresConfigRepository(session=session)

    model = repository.get_current_model_version("embedding")
    ranking = repository.get_current_ranking_config()
    matching = repository.get_current_matching_config()

    assert model is not None
    assert model.model_version_id == embedding_id
    assert ranking is not None
    assert ranking.ranking_config_id == ranking_id
    assert matching is not None
    assert matching.matching_config_id == matching_id
    assert "model_version" in session.operations[0][1]
    assert "is_current" in session.operations[0][1]


def test_production_config_repository_falls_back_for_reason_templates() -> None:
    session = ScriptedDatabaseSession(scripted_query_results=[[{"count": 0}]])
    repository = build_production_config_repository(session)

    assert isinstance(repository, ProductionConfigRepository)
    assert repository.count_active_reason_templates_by_type("summary") >= 1
    assert "reason_template" in session.operations[0][1]
