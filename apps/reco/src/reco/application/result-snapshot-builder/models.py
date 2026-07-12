"""Domain types for MOD-RECO-022 Result Snapshot Builder."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ItemSnapshot:
    """Item Snapshot domain (RecommendationResult定義書 §6.2.2)."""

    item_name_snapshot: str
    item_price_snapshot: int
    item_url_snapshot: str
    item_image_url_snapshot: str | None = None
    item_catchcopy_snapshot: str | None = None
    shop_name_snapshot: str | None = None
    review_average_snapshot: float | None = None
    review_count_snapshot: int | None = None


@dataclass(frozen=True)
class SnapshotBuilderInputItem:
    """021 出力明細（Snapshot 未充填）。"""

    recommendation_result_item_id: str
    recommendation_result_id: str
    item_id: str
    rank: int
    final_score: float
    context_score: float
    score_breakdown_json: dict[str, object] | None
    is_displayed: bool
    is_fallback: bool
    snapshot: ItemSnapshot | None = None


@dataclass(frozen=True)
class SnapshotBuilderInput:
    """Snapshot 構築の主入力。"""

    recommendation_result_id: str
    result_item_count: int
    items: tuple[SnapshotBuilderInputItem, ...]


@dataclass(frozen=True)
class ItemSourceRecord:
    """item 正本読取結果（§8.3.2）。"""

    item_id: str
    item_name: str | None
    price: int | None
    item_url: str | None
    catchcopy: str | None = None
    shop_code: str | None = None


@dataclass(frozen=True)
class ItemPrimaryImageRecord:
    """主画像 URL（is_primary=true）。"""

    item_id: str
    image_url: str


@dataclass(frozen=True)
class ItemReviewSnapshotRecord:
    """item_review_summary 読取結果。"""

    item_id: str
    review_average: float | None
    review_count: int | None


@dataclass(frozen=True)
class RecommendationResultItemInsertRow:
    """recommendation_result_item INSERT 行。"""

    recommendation_result_item_id: str
    recommendation_result_id: str
    item_id: str
    rank: int
    final_score: float
    context_score: float
    score_breakdown_json: dict[str, object] | None
    is_displayed: bool
    is_fallback: bool
    item_name_snapshot: str
    item_price_snapshot: int
    item_url_snapshot: str
    item_image_url_snapshot: str | None
    item_catchcopy_snapshot: str | None
    shop_name_snapshot: str | None
    review_average_snapshot: float | None
    review_count_snapshot: int | None


@dataclass(frozen=True)
class SnapshotBuilderRunMetrics:
    """Run 単位の構築観測値（§12.1）。"""

    snapshot_builder_item_count: int
    snapshot_builder_latency_ms: int
    snapshot_builder_items_persisted: bool
    snapshot_build_success: bool
    snapshot_null_image_count: int
    snapshot_null_review_count: int
