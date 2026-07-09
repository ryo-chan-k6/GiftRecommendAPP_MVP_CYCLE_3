"""Domain types for MOD-RECO-017 Popularity Scorer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ItemReviewSummary:
    """item_review_summary 行（候補 1 件分）。"""

    review_average: float | None
    review_count: int | None


@dataclass(frozen=True)
class PopularityWeights:
    """popularity_weights（§8.3.2）。"""

    w_rating: float
    w_review_count: float


@dataclass(frozen=True)
class PopularityScoreEntry:
    """候補ごとの Popularity Score 結果（§6.2.2）。"""

    item_id: str
    popularity_score: float
    popularity_formula: str
    calculated_at: datetime
    ranking_config_id: str
    signal_missing: bool
    rating_score: float | None = None
    review_count_score: float | None = None
    review_average_used: float | None = None
    review_count_used: int | None = None


@dataclass(frozen=True)
class PopularityScoreResult:
    """候補別 Popularity Score 結果集合。"""

    entries: tuple[PopularityScoreEntry, ...]
    max_review_count_in_candidates: int
    total_scored: int


@dataclass(frozen=True)
class PopularityScorerRunMetrics:
    """Run 単位の算出観測値（§12.1）。"""

    popularity_scorer_candidate_count: int
    popularity_scorer_latency_ms: int
    popularity_missing_signal_count: int
    popularity_score_value_out_of_range_count: int
