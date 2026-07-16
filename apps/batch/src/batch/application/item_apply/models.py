"""BATCH-007 domain models (in-memory / scaffold)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

ItemApplyRunStatus = Literal["succeeded", "partially_succeeded", "failed"]
DiffStatus = Literal["new", "updated", "unchanged", "unavailable"]

PROCESSABLE_DIFF_STATUSES: frozenset[str] = frozenset({"new", "updated", "unchanged"})


@dataclass(frozen=True)
class ProductDiffResultSeed:
    """plan / load_diff 入力となる product_diff_result 行（読取専用）."""

    product_diff_result_id: str
    batch_run_id: str
    staging_item_id: str
    external_item_code: str
    diff_status: DiffStatus
    old_hash: str | None = None
    new_hash: str | None = None


@dataclass(frozen=True)
class StagingImageSeed:
    """staging_item_image 行."""

    staging_item_id: str
    image_url: str
    image_size_type: str | None = None
    display_order: int = 0
    is_primary_candidate: bool = False


@dataclass(frozen=True)
class StagingItemSeed:
    """load_staging 入力となる staging_item 行."""

    staging_item_id: str
    source: str
    external_item_code: str
    normalized_hash: str | None
    item_name: str | None = None
    item_caption: str | None = None
    catchcopy: str | None = None
    price: int | None = None
    item_url: str | None = None
    external_genre_id: str | None = None
    shop_code: str | None = None
    availability: int | None = None
    review_average: float | None = None
    review_count: int | None = None


@dataclass(frozen=True)
class ItemSeed:
    """既存 item 行（読取 / Upsert 対象）."""

    source: str
    external_item_code: str
    normalized_hash: str | None
    item_id: str | None = None
    item_name: str | None = None
    item_caption: str | None = None
    catchcopy: str | None = None
    price: int | None = None
    item_url: str | None = None
    external_genre_id: str | None = None
    shop_code: str | None = None
    active_status: str | None = "active"
    is_active: bool | None = True
    first_fetched_at: datetime | None = None
    last_checked_at: datetime | None = None


@dataclass(frozen=True)
class ItemApplyPlan:
    """本 Run の Diff 選定キュー（仕様書 §8.2 plan / §18.1 No.12）."""

    items: tuple[ProductDiffResultSeed, ...]
    unavailable_skip_count: int
    source_filter: str
    max_items: int
    diff_batch_run_id: str | None


@dataclass
class ItemApplySyncResult:
    """BATCH-007 Run 結果サマリ."""

    batch_id: str
    job_run_id: str
    status: ItemApplyRunStatus = "failed"
    planned_diff_count: int = 0
    succeeded_external_codes: list[str] = field(default_factory=list)
    failed_external_codes: list[str] = field(default_factory=list)
    skipped_external_codes: list[str] = field(default_factory=list)
    item_upsert_count: int = 0
    item_unchanged_touch_count: int = 0
    item_unavailable_skip_count: int = 0
    item_image_sync_count: int = 0
    item_review_upsert_count: int = 0
    item_review_skip_count: int = 0
    completed_phases: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
    written_item_rows: list[dict[str, object]] = field(default_factory=list)
    written_item_image_rows: list[dict[str, object]] = field(default_factory=list)
    written_item_review_rows: list[dict[str, object]] = field(default_factory=list)
    written_active_status_rows: list[dict[str, object]] = field(default_factory=list)
    product_diff_write_count: int = 0
    hash_recalculate_calls: list[str] = field(default_factory=list)
