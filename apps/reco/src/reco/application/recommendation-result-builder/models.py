"""Domain types for MOD-RECO-021 Recommendation Result Builder."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ResultHeaderStatus(StrEnum):
    """DB ``result_status`` values set by this module (§8.3.4)."""

    GENERATED = "generated"
    EMPTY = "empty"


@dataclass(frozen=True)
class RecommendationResultHeaderInsertRow:
    """``recommendation_result`` header row for INSERT (§6.2.2)."""

    recommendation_result_id: str
    recommendation_request_id: str
    recommendation_run_id: str
    request_mode: str
    trace_id: str
    result_status: ResultHeaderStatus
    top_k: int
    result_item_count: int
    candidate_count: int | None
    fallback_used: bool
    semantic_config_version_id: str
    model_version_id: str
    matching_config_id: str
    ranking_config_id: str
    reason_template_version_id: str | None
    generated_at: datetime


@dataclass(frozen=True)
class BuiltRecommendationResultItem:
    """Result item domain prior to Snapshot attach (§6.2.2)."""

    recommendation_result_item_id: str
    recommendation_result_id: str
    item_id: str
    rank: int
    final_score: float
    context_score: float
    score_breakdown_json: dict[str, object] | None
    is_displayed: bool
    is_fallback: bool


@dataclass(frozen=True)
class BuiltRecommendationResult:
    """Header + item domains produced by Result Builder."""

    header: RecommendationResultHeaderInsertRow
    items: tuple[BuiltRecommendationResultItem, ...]


@dataclass(frozen=True)
class RecommendationResultBuilderRunMetrics:
    """Run 単位の構築観測値（§12.1）。"""

    result_builder_item_count: int
    result_builder_latency_ms: int
    result_builder_header_persisted: bool
    zero_result_header_count: int
    score_breakdown_partial_count: int
