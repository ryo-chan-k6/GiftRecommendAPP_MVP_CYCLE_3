"""MOD-RECO-025 Metric Logger constants."""

from __future__ import annotations

MODULE_ID = "MOD-RECO-025"
METRIC_SOURCE = "MOD-RECO-025"

TIER_2_METRIC_PREFIXES = frozenset(
    {
        "user_feature_distribution",
        "user_social_distribution",
        "user_symbolic_distribution",
        "lambda_ctx_distribution",
        "social_match_distribution",
        "symbolic_match_distribution",
        "feature_match_distribution",
        "final_score_distribution",
        "recommendation_run_count",
        "recommendation_success_count",
    }
)
