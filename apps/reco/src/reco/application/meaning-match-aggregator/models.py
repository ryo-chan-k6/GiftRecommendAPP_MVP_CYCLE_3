"""Domain types for MOD-RECO-015 Meaning Match Aggregator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MeaningMatchEntry:
    """候補ごとの Meaning Match 結果（§6.2.2）。"""

    item_id: str
    social_match: float
    symbolic_match: float
    aggregation_method: str
    calculated_at: datetime
    matching_config_id: str


@dataclass(frozen=True)
class MeaningMatchResult:
    """候補別 Meaning Match 結果集合。"""

    entries: tuple[MeaningMatchEntry, ...]
    total_aggregated: int


@dataclass(frozen=True)
class MeaningMatchAggregatorRunMetrics:
    """Run 単位の集約観測値（§12.1）。"""

    meaning_match_aggregator_candidate_count: int
    meaning_match_aggregator_latency_ms: int
    meaning_match_value_out_of_range_count: int
