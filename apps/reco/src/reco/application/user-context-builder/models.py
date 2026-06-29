"""Domain types for MOD-RECO-009."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PreferredContext:
    """Retrieval preferred query bundle (Retrieval §9.2)."""

    context_query: str
    embedding_query_text: str
    preferred_query: str | None = None
    free_text_query: str | None = None
    semantic_query: str | None = None


@dataclass(frozen=True)
class NonPreferredContext:
    """Avoid context kept separate from main retrieval query (UM-06)."""

    avoid_query_text: str | None = None


@dataclass(frozen=True)
class UserContext:
    """User Context domain object for downstream MOD-RECO-010+."""

    preferred_context: PreferredContext
    non_preferred_context: NonPreferredContext
    lambda_ctx: float


@dataclass(frozen=True)
class CompletedUserMeaning:
    """User Meaning after lambda_ctx assignment and INSERT."""

    recommendation_run_id: str
    user_social: float
    user_symbolic: float
    lambda_ctx: float
    feature_normalization_version_id: str
    user_meaning_id: str
    generated_at: datetime


@dataclass(frozen=True)
class UserMeaningInsertRow:
    """Single user_meaning INSERT row (IF-DB-RECO-003)."""

    recommendation_run_id: str
    feature_normalization_version_id: str
    user_social: float
    user_symbolic: float
    lambda_ctx: float
    generated_at: datetime


@dataclass(frozen=True)
class UserFeatureRow:
    """Read-only user_feature row for DB consistency validation."""

    feature_code: str
    feature_value: float
    feature_normalization_version_id: str
