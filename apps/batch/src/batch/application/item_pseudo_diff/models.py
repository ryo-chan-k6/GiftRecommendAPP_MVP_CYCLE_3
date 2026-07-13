"""BATCH-003 domain models (in-memory / scaffold)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

PseudoDiffRunStatus = Literal["succeeded", "partially_succeeded", "failed"]
CursorType = Literal["genre", "keyword", "update_sort", "ranking_supplement"]


@dataclass(frozen=True)
class FetchCursorRow:
    """fetch_cursor 走査単位（BATCH-003 が消費・更新）。"""

    cursor_type: CursorType
    cursor_id: str | None = None
    target_external_genre_id: str | None = None
    scope: dict[str, Any] = field(default_factory=dict)
    page: int = 1
    cursor_status: str = "active"
    scope_fingerprint: str | None = None


@dataclass(frozen=True)
class PseudoDiffFetchPlan:
    """本 Run の走査キュー（priority 解決後）。"""

    source: str
    cursors: tuple[FetchCursorRow, ...]
    max_pages: int
    hits: int


@dataclass(frozen=True)
class ProductCandidate:
    """商品候補（Raw 抽出結果。Item 正本ではない）。"""

    external_item_code: str
    item_name: str | None = None
    genre_id: str | None = None


@dataclass(frozen=True)
class RawItemSearchArtifact:
    """Raw JSON 保存単位。"""

    object_key: str
    content_hash: str
    api_call_log_id: str
    cursor_id: str | None
    cursor_type: str
    page: int
    body: bytes


@dataclass
class PseudoDiffSyncResult:
    """BATCH-003 Run 結果サマリ。"""

    batch_id: str
    job_run_id: str
    status: PseudoDiffRunStatus = "failed"
    planned_cursor_count: int = 0
    succeeded_cursor_ids: list[str] = field(default_factory=list)
    failed_cursor_ids: list[str] = field(default_factory=list)
    raw_save_success_count: int = 0
    candidate_item_code_count: int = 0
    ranking_supplement_consumed_count: int = 0
    completed_phases: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
    # Item / Staging を作っていないことの検証用（常に空であるべき）
    created_items: list[dict[str, object]] = field(default_factory=list)
    created_staging: list[dict[str, object]] = field(default_factory=list)
