from gift_recommendation.shared_logic.catalog import load_mvp_feature_codes
from gift_recommendation.shared_logic.constants import MVP_FEATURE_CODES


def test_load_mvp_feature_codes_matches_code_definitions() -> None:
    load_mvp_feature_codes.cache_clear()
    feature_codes = load_mvp_feature_codes()
    assert feature_codes == MVP_FEATURE_CODES
    assert len(feature_codes) == 8
