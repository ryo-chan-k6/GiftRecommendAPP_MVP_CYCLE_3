"""MOD-RECO-028 Phase Log Writer constants."""

from __future__ import annotations

MODULE_ID = "MOD-RECO-028"

OWNER_TYPE_RECOMMENDATION_RUN = "recommendation_run"

ALLOWED_RECOMMENDATION_RUN_PHASE_NAMES = frozenset(
    {
        "request_received",
        "config_resolved",
        "semantic_extracted",
        "user_feature_generated",
        "user_meaning_projected",
        "query_embedding_generated",
        "pre_hard_filter_completed",
        "retrieval_completed",
        "post_hard_filter_completed",
        "matching_completed",
        "ranking_completed",
        "result_generated",
        "reason_generated",
        "response_built",
    }
)

TERMINAL_PHASE_STATUSES = frozenset({"succeeded", "failed", "skipped"})
