"""Unit tests for PostgresNormalizationRuleRepository."""

from __future__ import annotations

from reco.infrastructure.db.repositories.postgres_normalization_rule_repository import (
    PostgresNormalizationRuleRepository,
)
from unit.infrastructure.db.helpers import ScriptedDatabaseSession


def test_get_active_binding_from_normalization_rule() -> None:
    session = ScriptedDatabaseSession(
        scripted_query_results=[
            [
                {
                    "feature_normalization_version_id": "norm-1",
                    "normalization_method": "sigmoid",
                    "parameter_json": {"center_feature": 0.5, "k_feature": 4.0},
                },
            ],
        ],
    )
    repo = PostgresNormalizationRuleRepository(session=session)
    binding = repo.get_active_normalization_binding("sem-1")
    assert binding is not None
    assert binding.feature_normalization_version_id == "norm-1"
    assert binding.parameters.center_feature == 0.5
    assert binding.parameters.k_feature == 4.0


def test_get_active_binding_falls_back_to_current_version() -> None:
    session = ScriptedDatabaseSession(
        scripted_query_results=[
            [],  # no normalization_rule
            [
                {
                    "feature_normalization_version_id": "norm-current",
                    "normalization_method": "sigmoid",
                    "parameter_json": {"center_feature": 0.4, "k_feature": 3.0},
                },
            ],
        ],
    )
    repo = PostgresNormalizationRuleRepository(session=session)
    binding = repo.get_active_normalization_binding("sem-missing")
    assert binding is not None
    assert binding.feature_normalization_version_id == "norm-current"
    assert binding.parameters.center_feature == 0.4


def test_get_active_binding_returns_none_when_missing() -> None:
    session = ScriptedDatabaseSession(scripted_query_results=[[], []])
    repo = PostgresNormalizationRuleRepository(session=session)
    assert repo.get_active_normalization_binding("sem-1") is None
