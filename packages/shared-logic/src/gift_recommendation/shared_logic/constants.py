"""MVP 固定 Feature コード定義。"""

from typing import Final

SOCIAL_FEATURE_CODES: Final[tuple[str, ...]] = (
    "formality",
    "safety",
    "brand_appropriateness",
)

SYMBOLIC_FEATURE_CODES: Final[tuple[str, ...]] = (
    "emotion",
    "novelty",
    "intimacy",
    "symbolic_identity",
    "story_richness",
)

MVP_FEATURE_CODES: Final[tuple[str, ...]] = SOCIAL_FEATURE_CODES + SYMBOLIC_FEATURE_CODES

FEATURE_VALUE_MIN: Final[float] = 0.0
FEATURE_VALUE_MAX: Final[float] = 1.0
