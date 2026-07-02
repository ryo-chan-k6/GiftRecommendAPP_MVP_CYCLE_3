"""Domain types for MOD-RECO-014 Feature Matcher."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FeatureAxisMatch:
    """Feature 別 distance / match 結果（§6.2.2.1）。"""

    distance: float
    match: float
    match_method: str | None = None
    imputed: bool = False


@dataclass(frozen=True)
class FeatureMatchEntry:
    """候補ごとの Feature Match 結果。"""

    item_id: str
    features: dict[str, FeatureAxisMatch]
    meaning_distance: float
    calculated_at: datetime
    avoid_similarity: float | None = None
    model_version_id: str | None = None


@dataclass(frozen=True)
class FeatureMatchResult:
    """Matching 結果集合（§6.2.2）。"""

    entries: tuple[FeatureMatchEntry, ...]
    total_matched: int
    total_excluded: int


@dataclass(frozen=True)
class FeatureMatcherRunMetrics:
    """Run 単位の Matching 観測値（§12.1）。"""

    feature_matcher_candidate_count: int
    feature_matcher_excluded_count: int
    feature_matcher_latency_ms: int
    feature_match_imputed_axis_count: int
    feature_value_out_of_range_count: int
