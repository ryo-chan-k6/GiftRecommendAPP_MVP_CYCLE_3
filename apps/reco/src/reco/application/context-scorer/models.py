"""Domain types for MOD-RECO-016 Context Scorer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ContextScoreEntry:
    """候補ごとの Context Score 結果（§6.2.2）。"""

    item_id: str
    context_score: float
    context_score_formula: str
    calculated_at: datetime
    matching_config_id: str


@dataclass(frozen=True)
class ContextScoreResult:
    """候補別 Context Score 結果集合。"""

    entries: tuple[ContextScoreEntry, ...]
    lambda_ctx_applied: float
    total_scored: int


@dataclass(frozen=True)
class ContextScorerRunMetrics:
    """Run 単位の算出観測値（§12.1）。"""

    context_scorer_candidate_count: int
    context_scorer_latency_ms: int
    context_score_value_out_of_range_count: int
    lambda_ctx_applied: float
