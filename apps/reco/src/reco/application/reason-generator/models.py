"""Domain types for MOD-RECO-023 Reason Generator."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReasonGeneratorInputItem:
    """022 完了後の Result Item（Reason 生成入力）。"""

    recommendation_result_item_id: str
    item_id: str
    rank: int
    final_score: float
    context_score: float
    score_breakdown_json: dict[str, object] | None
    is_fallback: bool


@dataclass(frozen=True)
class ReasonGeneratorInput:
    """Reason 生成の主入力。"""

    result_item_count: int
    items: tuple[ReasonGeneratorInputItem, ...]


@dataclass(frozen=True)
class SelectedFeature:
    """Reason 根拠として選定した Feature。"""

    feature_code: str
    match_score: float


@dataclass(frozen=True)
class SemanticEvidence:
    """item_semantic 由来の根拠。"""

    concept_code: str
    evidence_text: str
    confidence: float | None = None


@dataclass(frozen=True)
class ReasonTemplateRecord:
    """reason_template 読取結果。"""

    reason_template_id: str
    template_name: str
    template_version: int
    template_type: str
    template_body: str
    relationship_code: str | None = None
    occasion_code: str | None = None
    feature_code: str | None = None


@dataclass(frozen=True)
class ItemSemanticRecord:
    """item_semantic 読取結果（§8.3.8）。"""

    item_id: str
    semantic_config_version_id: str
    concepts: tuple[SemanticEvidence, ...] = ()


@dataclass(frozen=True)
class GeneratedReason:
    """1 Item 分の Reason 生成結果。"""

    recommendation_result_item_id: str
    item_id: str
    template_id: str
    reason_summary: str
    reason_detail: str | None
    reason_points: tuple[str, ...]
    reason_badges: tuple[str, ...]
    caution_note: str | None
    reason_basis_json: dict[str, object]
    is_fallback: bool
    recommendation_reason_id: str | None = None


@dataclass(frozen=True)
class RecommendationReasonInsertRow:
    """recommendation_reason INSERT 行。"""

    recommendation_reason_id: str
    recommendation_result_item_id: str
    template_id: str
    reason_summary: str
    reason_detail: str | None
    reason_points_json: list[str] | None
    reason_badges_json: list[str] | None
    caution_note: str | None
    reason_basis_json: dict[str, object]


@dataclass(frozen=True)
class ReasonGeneratorRunMetrics:
    """Run 単位の Reason 生成観測値（§12.1）。"""

    reason_generator_item_count: int
    reason_generator_success_count: int
    reason_generator_fallback_count: int
    reason_generator_persisted: bool
    reason_generation_latency_ms: int
