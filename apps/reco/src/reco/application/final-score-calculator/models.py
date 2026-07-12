"""Domain types for MOD-RECO-019 Final Score Calculator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RankingWeightsUsed:
    """ranking_weights（§8.3.2）。"""

    w_context: float
    w_popularity: float
    w_risk: float


@dataclass(frozen=True)
class FinalScoreEntry:
    """候補ごとの Final Score 結果（§6.2.2）。"""

    item_id: str
    context_score: float
    popularity_score: float
    risk_penalty: float
    pre_rank_score: float
    diversity_penalty: float
    final_score: float
    score_breakdown: dict[str, object]
    final_score_formula: str
    ranking_weights_used: RankingWeightsUsed
    calculated_at: datetime
    ranking_config_id: str


@dataclass(frozen=True)
class FinalScoreResult:
    """候補別 Final Score 結果集合。"""

    entries: tuple[FinalScoreEntry, ...]
    total_scored: int


@dataclass(frozen=True)
class FinalScoreCalculatorRunMetrics:
    """Run 単位の算出観測値（§12.1）。"""

    final_score_calculator_candidate_count: int
    final_score_calculator_latency_ms: int
    final_score_excluded_candidate_count: int
    final_score_value_out_of_range_count: int
