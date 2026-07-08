from gift_recommendation.shared_logic.constants import MVP_FEATURE_CODES
from gift_recommendation.shared_logic.meaning_projection import project_to_meaning
from gift_recommendation.shared_logic.types import ProjectionWeights


def test_project_to_meaning_uses_equal_weights_by_default() -> None:
    vector = {code: 0.0 for code in MVP_FEATURE_CODES}
    vector.update(
        {
            "formality": 0.6,
            "safety": 0.8,
            "brand_appropriateness": 1.0,
            "emotion": 0.2,
            "novelty": 0.4,
            "intimacy": 0.6,
            "symbolic_identity": 0.8,
            "story_richness": 1.0,
        }
    )

    meaning = project_to_meaning(vector, feature_codes=MVP_FEATURE_CODES)

    assert meaning.social == (0.6 + 0.8 + 1.0) / 3
    assert meaning.symbolic == (0.2 + 0.4 + 0.6 + 0.8 + 1.0) / 5


def test_project_to_meaning_supports_custom_weights() -> None:
    vector = {code: 0.5 for code in MVP_FEATURE_CODES}
    vector["formality"] = 1.0
    vector["emotion"] = 1.0

    weights = ProjectionWeights(formality=2.0, emotion=3.0)
    meaning = project_to_meaning(
        vector,
        weights=weights,
        feature_codes=MVP_FEATURE_CODES,
    )

    assert meaning.social == (2.0 * 1.0 + 0.5 + 0.5) / (2.0 + 1.0 + 1.0)
    assert meaning.symbolic == (3.0 * 1.0 + 0.5 * 4) / (3.0 + 4.0)
