import pytest

from gift_recommendation.shared_logic.constants import MVP_FEATURE_CODES
from gift_recommendation.shared_logic.errors import IncompleteFeatureVectorError
from gift_recommendation.shared_logic.normalization import NormalizationMethod, normalize_features


def _full_vector(value: float) -> dict[str, float]:
    return {code: value for code in MVP_FEATURE_CODES}


def test_normalize_features_uses_rule_based_clip() -> None:
    raw = _full_vector(1.2)
    raw["safety"] = -0.3

    normalized = normalize_features(raw, feature_codes=MVP_FEATURE_CODES)

    assert normalized["formality"] == 1.0
    assert normalized["safety"] == 0.0


def test_normalize_features_requires_complete_vector() -> None:
    with pytest.raises(IncompleteFeatureVectorError):
        normalize_features({"formality": 0.5}, feature_codes=MVP_FEATURE_CODES)


def test_normalization_method_default_is_rule_based_clip() -> None:
    assert NormalizationMethod.RULE_BASED_CLIP.value == "rule_based_clip"
