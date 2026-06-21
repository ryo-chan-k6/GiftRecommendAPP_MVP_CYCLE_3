import pytest

from gift_recommendation.shared_logic.constants import MVP_FEATURE_CODES
from gift_recommendation.shared_logic.errors import IncompleteFeatureVectorError
from gift_recommendation.shared_logic.feature_engine import (
    clip_feature_vector,
    integrate_feature_deltas,
    validate_complete_feature_vector,
)


def test_integrate_feature_deltas_merges_base_and_delta() -> None:
    base = {"formality": 0.2, "safety": 0.3}
    deltas = {"formality": 0.5, "emotion": 0.4}

    merged = integrate_feature_deltas(base, deltas, feature_codes=MVP_FEATURE_CODES)

    assert merged["formality"] == pytest.approx(0.7)
    assert merged["safety"] == pytest.approx(0.3)
    assert merged["emotion"] == pytest.approx(0.4)
    assert merged["brand_appropriateness"] == pytest.approx(0.0)


def test_clip_feature_vector_clamps_out_of_range_values() -> None:
    vector = {code: 1.5 for code in MVP_FEATURE_CODES}
    vector["safety"] = -0.2

    clipped = clip_feature_vector(vector, feature_codes=MVP_FEATURE_CODES)

    assert clipped["formality"] == 1.0
    assert clipped["safety"] == 0.0


def test_validate_complete_feature_vector_raises_for_missing_axes() -> None:
    with pytest.raises(IncompleteFeatureVectorError) as exc_info:
        validate_complete_feature_vector(
            {"formality": 0.5},
            feature_codes=MVP_FEATURE_CODES,
        )

    assert "story_richness" in exc_info.value.missing_codes
