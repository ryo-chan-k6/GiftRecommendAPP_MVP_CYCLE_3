"""BATCH-006 domain models (in-memory / scaffold)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

ProductDiffRunStatus = Literal["succeeded", "partially_succeeded", "failed"]
DiffStatus = Literal["new", "updated", "unchanged", "unavailable"]


@dataclass(frozen=True)
class StagingItemSeed:
    """Plan / load 入力となる staging_item 行."""

    staging_item_id: str
    source: str
    external_item_code: str
    normalized_hash: str | None
    item_name: str | None = None
    item_url: str | None = None
    price: int | None = None
    availability: int | None = None
    diff_status: str | None = None
    # Validator 不合格 / 取得不能引き継ぎ（§18.1 No.9 (c)）
    validation_failed: bool = False
    fetch_unavailable: bool = False


@dataclass(frozen=True)
class ItemSeed:
    """resolve_item で突合する既存 item 行（読取のみ）."""

    source: str
    external_item_code: str
    normalized_hash: str | None
    item_id: str | None = None
    # 境界検証用: 本 Batch が触ってはならない業務列のスナップショット
    item_name: str | None = None
    active_status: str | None = None


@dataclass(frozen=True)
class ProductDiffPlan:
    """本 Run の Staging 選定キュー（仕様書 §8.2 plan / §18.1 No.8）."""

    items: tuple[StagingItemSeed, ...]
    source_filter: str
    max_items: int
    force: bool
    sync_staging_diff_status: bool


@dataclass(frozen=True)
class DiffJudgment:
    """compare 結果（persist 候補）."""

    staging_item_id: str
    external_item_code: str
    diff_status: DiffStatus
    old_hash: str | None
    new_hash: str
    judged_at: datetime


@dataclass
class ProductDiffSyncResult:
    """BATCH-006 Run 結果サマリ."""

    batch_id: str
    job_run_id: str
    status: ProductDiffRunStatus = "failed"
    planned_staging_count: int = 0
    succeeded_external_codes: list[str] = field(default_factory=list)
    failed_external_codes: list[str] = field(default_factory=list)
    skipped_external_codes: list[str] = field(default_factory=list)
    diff_new_count: int = 0
    diff_updated_count: int = 0
    diff_unchanged_count: int = 0
    diff_unavailable_count: int = 0
    product_diff_upsert_count: int = 0
    staging_diff_status_sync_count: int = 0
    completed_phases: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
    # 境界検証: Item / item_image / active_status を書いていないこと
    written_item_rows: list[dict[str, object]] = field(default_factory=list)
    written_item_image_rows: list[dict[str, object]] = field(default_factory=list)
    written_active_status_rows: list[dict[str, object]] = field(default_factory=list)
    # hash 再算出が起きていないことの検証用（常に空）
    hash_recalculate_calls: list[str] = field(default_factory=list)
