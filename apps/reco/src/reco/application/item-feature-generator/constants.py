"""MOD-RECO-027 Item Feature Generator constants."""

from __future__ import annotations

MODULE_ID = "MOD-RECO-027"
SURFACE_ERROR_CODE = "GRS-BAT-008"

NEUTRAL_BASE = 0.5
FEATURE_INPUT_HASH_LENGTH = 64

POLARITY_POSITIVE = "positive"
POLARITY_NEGATIVE = "negative"
POLARITY_MIXED = "mixed"

# Featureルール定義書 §13.2（Item source_weight 抜粋）
SOURCE_WEIGHT_BY_TYPE: dict[str, float] = {
    "item_description": 1.00,
    "item_caption": 0.90,
    "item_name": 0.80,
    "item_brand": 0.80,
    "item_tag": 0.70,
    "item_genre": 0.60,
    "item_review": 0.50,
}

DEFAULT_FEATURE_NORMALIZATION_VERSION_ID = "fnv-mvp-item-feature-default"
