"""BATCH-005 domain models (in-memory / scaffold)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

RawStagingRunStatus = Literal["succeeded", "partially_succeeded", "failed"]
SourceApi = Literal["item_search", "item_ranking", "genre_search", "attribute_search"]


@dataclass(frozen=True)
class RawMetadataSeed:
    """Plan 入力となる raw_product_metadata 行."""

    raw_metadata_id: str
    object_key: str
    content_hash: str
    source: str = "rakuten"
    source_api: str = "item_search"
    import_status: str = "raw_saved"
    batch_run_id: str | None = None
    bucket: str | None = None


@dataclass(frozen=True)
class StagingPlan:
    """本 Run の Raw 選定キュー（仕様書 §8.2 plan / §18.1 No.2）."""

    items: tuple[RawMetadataSeed, ...]
    source_api_filter: tuple[str, ...]
    max_raw: int
    force: bool


@dataclass(frozen=True)
class StagingItemRow:
    """staging_item へ upsert する候補行."""

    raw_metadata_id: str
    source: str
    external_item_code: str
    item_name: str
    item_url: str
    price: int
    normalized_hash: str
    item_caption: str | None = None
    catchcopy: str | None = None
    external_genre_id: int | None = None
    shop_code: str | None = None
    availability: int | None = None
    review_average: float | None = None
    review_count: int | None = None
    diff_status: str | None = None
    staged_at: datetime | None = None


@dataclass(frozen=True)
class StagingItemImageRow:
    """staging_item_image へ upsert する候補行."""

    raw_metadata_id: str
    external_item_code: str
    image_url: str
    image_size_type: Literal["small", "medium"]
    display_order: int
    is_primary_candidate: bool
    staged_at: datetime | None = None


@dataclass(frozen=True)
class ItemTransformBundle:
    """1 商品分の transform 結果（item + images）."""

    item: StagingItemRow
    images: tuple[StagingItemImageRow, ...]
    normalized_payload: dict[str, Any]


@dataclass(frozen=True)
class StagingRankingSignalRow:
    """staging_ranking_signal へ upsert する候補行."""

    raw_metadata_id: str
    external_item_code: str
    external_genre_id: int
    rank: int
    period: str
    last_build_date: datetime
    staged_at: datetime | None = None


@dataclass(frozen=True)
class StagingGenreRow:
    """staging_genre へ upsert する候補行."""

    raw_metadata_id: str
    source: str
    external_genre_id: int
    genre_name: str
    parent_external_genre_id: int | None
    genre_level: int
    is_leaf: bool
    staged_at: datetime | None = None


@dataclass(frozen=True)
class RawTransformResult:
    """1 Raw 分の transform 結果."""

    raw_metadata_id: str
    source_api: str
    items: tuple[ItemTransformBundle, ...] = ()
    ranking_rows: tuple[StagingRankingSignalRow, ...] = ()
    genre_rows: tuple[StagingGenreRow, ...] = ()
    skipped: bool = False
    skip_reason: str | None = None


@dataclass
class RawStagingSyncResult:
    """BATCH-005 Run 結果サマリ."""

    batch_id: str
    job_run_id: str
    status: RawStagingRunStatus = "failed"
    planned_raw_count: int = 0
    succeeded_raw_ids: list[str] = field(default_factory=list)
    failed_raw_ids: list[str] = field(default_factory=list)
    skipped_raw_ids: list[str] = field(default_factory=list)
    staging_item_upsert_count: int = 0
    staging_item_image_upsert_count: int = 0
    staging_ranking_signal_upsert_count: int = 0
    staging_genre_upsert_count: int = 0
    validation_reject_count: int = 0
    completed_phases: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
    # 境界検証: Item / product_diff / active_status / external_genre を書いていないこと
    written_item_rows: list[dict[str, object]] = field(default_factory=list)
    written_product_diff_rows: list[dict[str, object]] = field(default_factory=list)
    written_active_status_rows: list[dict[str, object]] = field(default_factory=list)
    written_external_genre_rows: list[dict[str, object]] = field(default_factory=list)
    object_storage_put_count: int = 0
    object_storage_delete_count: int = 0
