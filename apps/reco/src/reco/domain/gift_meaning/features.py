"""MVP Gift Meaning feature definitions (Phase4a scaffold)."""

from __future__ import annotations

from typing import Final, Mapping

# packages/shared-logic と同一の MVP 固定 Feature コード。Phase4b で shared-logic へ委譲する。
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

FeatureVector = Mapping[str, float]
