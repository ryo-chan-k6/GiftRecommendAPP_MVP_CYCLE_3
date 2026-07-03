"""Domain types for MOD-RECO-020 Final Ranker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RankedItemEntry:
    """選定済み候補 1 件（§6.2.2）。"""

    item_id: str
    rank: int
    final_score: float
    pre_rank_score: float
    diversity_penalty: float
    score_breakdown: dict[str, object]
    is_displayed: bool
    ranking_config_id: str
    diversity_method: str
    selected_at: datetime
    mmr_score: float | None = None
    max_similarity_to_selected: float | None = None


@dataclass(frozen=True)
class RankedItems:
    """順位付き候補集合。"""

    entries: tuple[RankedItemEntry, ...]
    total_selected: int
    top_k_used: int
    mmr_candidate_pool_size: int
    mmr_applied: bool
    lambda_mmr_used: float | None = None


@dataclass(frozen=True)
class RankingParams:
    """MMR / top_k 解決結果。"""

    top_k: int
    top_k_clipped: bool
    lambda_mmr: float
    lambda_mmr_clipped: bool
    mmr_candidate_limit: int
    diversity_method: str
    ranking_config_id: str


@dataclass(frozen=True)
class FinalRankerRunMetrics:
    """Run 単位の選定観測値（§12.1）。"""

    final_ranker_selected_count: int
    final_ranker_latency_ms: int
    final_ranker_mmr_applied: bool
    mmr_rank_shift_count: int
    final_ranker_feature_match_missing_count: int
    top_k_clipped: bool
