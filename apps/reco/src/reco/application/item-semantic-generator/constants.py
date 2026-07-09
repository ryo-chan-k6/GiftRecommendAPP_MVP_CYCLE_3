"""MOD-RECO-026 Item Semantic Generator constants."""

from __future__ import annotations

MODULE_ID = "MOD-RECO-026"
SURFACE_ERROR_CODE = "GRS-BAT-008"

CONFIDENCE_ADOPTION_THRESHOLD = 0.60
CONFIDENCE_WEAK_MIN = 0.40
CONFIDENCE_HIGH = 0.80
DEFAULT_EXTRACTION_METHOD = "hybrid"
DEFAULT_INPUT_INTENT = "neutral"

SOURCE_TYPE_CONFIDENCE_ADJUSTMENTS: dict[str, float] = {
    "item_description": 0.0,
    "item_caption": 0.0,
    "item_name": -0.05,
    "item_genre": 0.0,
    "item_tag": 0.0,
    "item_review": 0.0,
    "item_brand": 0.0,
}

NEGATION_REVIEW_MARKERS: tuple[str, ...] = (
    "安っぽい",
    "残念",
    "期待外れ",
    "がっかり",
    "思ったより",
    "あまり",
    "よくない",
    "最悪",
    "微妙",
    "がっかり",
)
