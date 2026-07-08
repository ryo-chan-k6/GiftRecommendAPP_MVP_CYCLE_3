"""Domain types for MOD-RECO-018 Risk Scorer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RiskWeights:
    """risk_weights（§8.3.2）。"""

    w_avoid: float
    w_social: float
    w_data_quality: float


@dataclass(frozen=True)
class RiskPenaltyEntry:
    """候補ごとの Risk Penalty 結果（§6.2.2）。"""

    item_id: str
    risk_penalty: float
    risk_formula: str
    calculated_at: datetime
    ranking_config_id: str
    signal_missing: bool
    avoid_risk: float | None = None
    social_low_risk: float | None = None
    data_quality_risk: float | None = None
    avoid_similarity_used: float | None = None
    social_match_used: float | None = None
    item_feature_confidence_used: float | None = None


@dataclass(frozen=True)
class RiskPenaltyResult:
    """候補別 Risk Penalty 結果集合。"""

    entries: tuple[RiskPenaltyEntry, ...]
    total_scored: int


@dataclass(frozen=True)
class RiskScorerRunMetrics:
    """Run 単位の算出観測値（§12.1）。"""

    risk_scorer_candidate_count: int
    risk_scorer_latency_ms: int
    risk_missing_signal_count: int
    risk_penalty_value_out_of_range_count: int
    avoid_risk_nonzero_count: int
