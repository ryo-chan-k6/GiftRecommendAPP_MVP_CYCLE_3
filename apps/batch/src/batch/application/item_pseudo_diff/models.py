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
    """本 Run の走査キュー（priority 解決後）。

    ``pages_per_run`` / ``cursors_per_run`` / ``wall_clock_seconds`` は
    1 Run の進行量上限（Run予算）。カタログ深さ打ち切りではない。
    ``cursors_per_run=None`` は計画上の全 active cursor を対象（CLI は既定 1）。
    ``max_pages`` は互換 alias（= pages_per_run）。
    """

    source: str
    cursors: tuple[FetchCursorRow, ...]
    pages_per_run: int
    hits: int
    cursors_per_run: int | None = None
    wall_clock_seconds: int | None = None

    @property
    def max_pages(self) -> int:
        """後方互換: 旧 max_pages = Run予算の pages_per_run。"""

        return self.pages_per_run


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
    skipped_inactive_cursor_count: int = 0
    pages_fetched: int = 0
    cursors_started: int = 0
    run_budget_stopped: bool = False
    raw_save_success_count: int = 0
    candidate_item_code_count: int = 0
    ranking_supplement_consumed_count: int = 0
    completed_phases: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
    # Item / Staging を作っていないことの検証用（常に空であるべき）
    created_items: list[dict[str, object]] = field(default_factory=list)
    created_staging: list[dict[str, object]] = field(default_factory=list)
