from gift_recommendation.test_fixtures import (
    FIXTURE_SCHEMA_VERSION,
    load_fixture_manifest,
    load_mvp_user_features_baseline,
    load_recommendation_request_boss_thanks_minimal,
)


def test_load_fixture_manifest() -> None:
    load_fixture_manifest.cache_clear()
    manifest = load_fixture_manifest()

    assert manifest["schemaVersion"] == FIXTURE_SCHEMA_VERSION
    assert manifest["packageId"] == "packages-test-fixtures"
    assert "mvp_user_features_baseline" in manifest["items"]


def test_load_mvp_user_features_baseline() -> None:
    load_fixture_manifest.cache_clear()
    fixture = load_mvp_user_features_baseline()

    assert len(fixture["featureCodes"]) == 8
    assert fixture["values"]["formality"] == 0.75


def test_load_recommendation_request_boss_thanks_minimal() -> None:
    load_fixture_manifest.cache_clear()
    fixture = load_recommendation_request_boss_thanks_minimal()

    assert fixture["relationship"]["relationshipCode"] == "boss"
    assert fixture["occasion"]["occasionCode"] == "thanks"
    assert fixture["budget"]["budgetMax"] == 5000
