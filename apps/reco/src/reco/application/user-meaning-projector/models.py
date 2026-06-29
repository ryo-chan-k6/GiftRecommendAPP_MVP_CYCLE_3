"""Domain types for MOD-RECO-008."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MeaningProjectionWeights:
    """Social / Symbolic projection weights from semantic_config_version."""

    w_formality: float | None = None
    w_safety: float | None = None
    w_brand_appropriateness: float | None = None
    w_emotion: float | None = None
    w_novelty: float | None = None
    w_intimacy: float | None = None
    w_symbolic_identity: float | None = None
    w_story_richness: float | None = None


@dataclass(frozen=True)
class UserFeatureRow:
    """Read-only user_feature row for DB consistency validation."""

    feature_code: str
    feature_value: float
    feature_normalization_version_id: str


@dataclass(frozen=True)
class UserMeaningProjection:
    """Projected User Meaning (Social / Symbolic only; lambda_ctx is MOD-RECO-009)."""

    recommendation_run_id: str
    user_social: float
    user_symbolic: float
    feature_normalization_version_id: str
    projected_at: datetime
