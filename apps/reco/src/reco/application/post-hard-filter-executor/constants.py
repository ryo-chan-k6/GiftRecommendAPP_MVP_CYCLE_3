"""MOD-RECO-013 Post Hard Filter Executor constants."""

from __future__ import annotations

MODULE_ID = "MOD-RECO-013"
PHASE_NAME = "post_hard_filter_completed"
SURFACE_ERROR_CODE = "GRS-REC-010"

NG_CONFIDENCE_THRESHOLD = 0.60
AVOID_CONFIDENCE_THRESHOLD = 0.60
ITEM_SEMANTIC_CONFIDENCE_THRESHOLD = 0.60

INPUT_INTENT_NG_CANDIDATE = "ng_candidate"
INPUT_INTENT_AVOID = "avoid"

REASON_SEMANTIC_NG = "semantic_ng"
REASON_DUPLICATE = "duplicate"
REASON_INCONSISTENCY = "inconsistency"
REASON_DISPLAY_VALIDATION = "display_validation"

VALIDATION_STATUS_PASSED = "passed"
