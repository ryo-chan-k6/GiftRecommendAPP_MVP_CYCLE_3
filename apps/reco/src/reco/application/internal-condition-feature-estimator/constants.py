"""MOD-RECO-006 Internal Condition Feature Estimator constants."""

from __future__ import annotations

MODULE_ID = "MOD-RECO-006"
PHASE_NAME = "internal_feature_estimated"
SURFACE_ERROR_CODE = "GRS-REC-005"
ESTIMATION_METHOD_RULE = "rule"

CONFIDENCE_THRESHOLD = 0.60
DEFAULT_FREE_TEXT_WEIGHT = 0.70

INTERNAL_SOURCE_TYPES = frozenset(
    {
        "preferred_condition",
        "non_preferred_condition",
        "free_text",
    },
)

POLARITY_POSITIVE = "positive"
POLARITY_NEGATIVE = "negative"
POLARITY_MIXED = "mixed"
