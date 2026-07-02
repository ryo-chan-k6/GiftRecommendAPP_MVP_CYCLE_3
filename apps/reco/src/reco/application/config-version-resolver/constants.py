"""MOD-RECO-003 Config Version Resolver constants."""

from __future__ import annotations

from typing import Final

MODULE_ID: Final[str] = "MOD-RECO-003"

DEFAULT_SEMANTIC_CONFIG_NAME: Final[str] = "mvp_semantic_config"

REQUIRED_MODEL_TYPES: Final[tuple[str, ...]] = ("embedding", "llm", "ranking")

REASON_TEMPLATE_TYPES: Final[tuple[str, ...]] = (
    "summary",
    "detail",
    "point",
    "caution",
)

SOCIAL_FEATURE_WEIGHT_KEYS: Final[tuple[str, ...]] = (
    "formality",
    "safety",
    "brand_appropriateness",
)

SYMBOLIC_FEATURE_WEIGHT_KEYS: Final[tuple[str, ...]] = (
    "emotion",
    "novelty",
    "intimacy",
    "symbolic_identity",
    "story_richness",
)

SURFACE_ERROR_CODE: Final[str] = "GRS-REC-003"
