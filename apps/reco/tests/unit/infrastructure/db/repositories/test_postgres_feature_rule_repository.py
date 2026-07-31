"""PostgresFeatureRuleRepository unit tests."""

from __future__ import annotations

from decimal import Decimal

from reco.application.external_condition_feature_estimator.constants import (
    DEFAULT_OCCASION_WEIGHT,
    DEFAULT_RELATIONSHIP_WEIGHT,
)
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES
from reco.infrastructure.db.repositories.postgres_feature_rule_repository import (
    PostgresFeatureRuleRepository,
)
from unit.infrastructure.db.helpers import ScriptedDatabaseSession


def _feature_rows(value_column: str, *, start: float = 0.1) -> list[dict[str, object]]:
    return [
        {
            "feature_code": feature_code,
            value_column: Decimal(str(start + index / 10)),
        }
        for index, feature_code in enumerate(MVP_FEATURE_CODES)
    ]


def _integration_rows(
    *,
    relationship_weight: float = 0.4,
    occasion_weight: float = 0.6,
) -> list[dict[str, object]]:
    return [
        {
            "feature_code": feature_code,
            "input_source": input_source,
            "weight": Decimal(str(weight)),
        }
        for feature_code in MVP_FEATURE_CODES
        for input_source, weight in (
            ("relationship_feature", relationship_weight),
            ("occasion_feature", occasion_weight),
        )
    ]


def test_get_relationship_features_returns_eight_active_versioned_features() -> None:
    session = ScriptedDatabaseSession(
        scripted_query_results=[_feature_rows("feature_base_value")],
    )
    repository = PostgresFeatureRuleRepository(session=session)

    result = repository.get_relationship_features("spouse", "semantic-v1")

    assert result is not None
    assert set(result) == set(MVP_FEATURE_CODES)
    assert result["formality"] == 0.1
    _, sql, params = session.operations[0]
    assert "FROM relationship_rule" in sql
    assert "semantic_config_version_id = %s" in sql
    assert "relationship_code = %s" in sql
    assert "is_active = true" in sql
    assert params == ("semantic-v1", "spouse")


def test_get_occasion_features_returns_eight_active_versioned_features() -> None:
    session = ScriptedDatabaseSession(
        scripted_query_results=[_feature_rows("feature_base_value", start=0.2)],
    )
    repository = PostgresFeatureRuleRepository(session=session)

    result = repository.get_occasion_features("wedding_gift", "semantic-v1")

    assert result is not None
    assert set(result) == set(MVP_FEATURE_CODES)
    assert result["formality"] == 0.2
    _, sql, params = session.operations[0]
    assert "FROM occasion_rule" in sql
    assert "semantic_config_version_id = %s" in sql
    assert "occasion_code = %s" in sql
    assert "is_active = true" in sql
    assert params == ("semantic-v1", "wedding_gift")


def test_base_feature_lookup_returns_none_when_no_rows_exist() -> None:
    session = ScriptedDatabaseSession(scripted_query_results=[[], []])
    repository = PostgresFeatureRuleRepository(session=session)

    assert repository.get_relationship_features("missing", "semantic-v1") is None
    assert repository.get_occasion_features("missing", "semantic-v1") is None


def test_base_feature_lookup_preserves_partial_vector_for_completeness_validation() -> None:
    partial_rows = _feature_rows("feature_base_value")[:-1]
    session = ScriptedDatabaseSession(scripted_query_results=[partial_rows])
    repository = PostgresFeatureRuleRepository(session=session)

    result = repository.get_relationship_features("spouse", "semantic-v1")

    assert result is not None
    assert set(result) == set(MVP_FEATURE_CODES[:-1])


def test_get_pair_delta_resolves_pair_master_and_returns_eight_features() -> None:
    session = ScriptedDatabaseSession(
        scripted_query_results=[
            [{"pair_id": "pair-1"}],
            _feature_rows("feature_delta", start=-0.3),
        ],
    )
    repository = PostgresFeatureRuleRepository(session=session)

    result = repository.get_pair_delta("lover", "birthday", "semantic-v1")

    assert result is not None
    assert set(result) == set(MVP_FEATURE_CODES)
    assert result["formality"] == -0.3
    _, pair_master_sql, pair_master_params = session.operations[0]
    assert "FROM pair_master" in pair_master_sql
    assert "is_active = true" in pair_master_sql
    assert pair_master_params == ("lover", "birthday")
    _, pair_rule_sql, pair_rule_params = session.operations[1]
    assert "FROM pair_rule" in pair_rule_sql
    assert "semantic_config_version_id = %s" in pair_rule_sql
    assert "is_active = true" in pair_rule_sql
    assert pair_rule_params == ("semantic-v1", "pair-1")


def test_get_pair_delta_returns_none_when_pair_is_undefined() -> None:
    session = ScriptedDatabaseSession(scripted_query_results=[[]])
    repository = PostgresFeatureRuleRepository(session=session)

    assert repository.get_pair_delta("spouse", "other", "semantic-v1") is None
    assert len(session.operations) == 1


def test_get_pair_delta_returns_none_when_pair_rule_has_no_rows() -> None:
    session = ScriptedDatabaseSession(
        scripted_query_results=[[{"pair_id": "pair-1"}], []],
    )
    repository = PostgresFeatureRuleRepository(session=session)

    assert repository.get_pair_delta("spouse", "other", "semantic-v1") is None
    assert len(session.operations) == 2


def test_get_integration_weights_maps_common_weights_for_all_eight_axes() -> None:
    session = ScriptedDatabaseSession(
        scripted_query_results=[_integration_rows()],
    )
    repository = PostgresFeatureRuleRepository(session=session)

    result = repository.get_integration_weights("semantic-v1")

    assert result.relationship_weight == 0.4
    assert result.occasion_weight == 0.6
    _, sql, params = session.operations[0]
    assert "FROM feature_integration_rule" in sql
    assert "semantic_config_version_id = %s" in sql
    assert "is_active = true" in sql
    assert params == ("semantic-v1",)


def test_get_integration_weights_falls_back_when_axes_are_missing() -> None:
    rows = _integration_rows()
    rows = [
        row
        for row in rows
        if row["feature_code"] != MVP_FEATURE_CODES[-1]
    ]
    session = ScriptedDatabaseSession(scripted_query_results=[rows])
    repository = PostgresFeatureRuleRepository(session=session)

    result = repository.get_integration_weights("semantic-v1")

    assert result.relationship_weight == DEFAULT_RELATIONSHIP_WEIGHT
    assert result.occasion_weight == DEFAULT_OCCASION_WEIGHT


def test_get_integration_weights_falls_back_only_for_inconsistent_source() -> None:
    rows = _integration_rows()
    rows[0]["weight"] = Decimal("0.9")
    session = ScriptedDatabaseSession(scripted_query_results=[rows])
    repository = PostgresFeatureRuleRepository(session=session)

    result = repository.get_integration_weights("semantic-v1")

    assert result.relationship_weight == DEFAULT_RELATIONSHIP_WEIGHT
    assert result.occasion_weight == 0.6


def test_get_integration_weights_falls_back_when_no_rows_exist() -> None:
    session = ScriptedDatabaseSession(scripted_query_results=[[]])
    repository = PostgresFeatureRuleRepository(session=session)

    result = repository.get_integration_weights("semantic-v1")

    assert result.relationship_weight == DEFAULT_RELATIONSHIP_WEIGHT
    assert result.occasion_weight == DEFAULT_OCCASION_WEIGHT
