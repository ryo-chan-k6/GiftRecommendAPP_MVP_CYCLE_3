"""MOD-RECO-029 Error Log Writer constants."""

from __future__ import annotations

import re

MODULE_ID = "MOD-RECO-029"

ALLOWED_OWNER_TYPES = frozenset(
    {
        "recommendation_request",
        "recommendation_run",
        "recommendation_result",
        "recommendation_feedback",
        "batch_run",
        "api_call",
        "raw_product_metadata",
        "item_generation_queue",
        "evaluation_run",
        "system",
    }
)

ALLOWED_SEVERITIES = frozenset({"warn", "error", "critical"})

ALLOWED_SERVICES = frozenset({"api", "reco", "batch"})

GRS_ERROR_CODE_PATTERN = re.compile(r"^GRS-[A-Z]{2,4}-\d{3}$")
