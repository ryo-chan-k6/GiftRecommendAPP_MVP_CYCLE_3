"""BATCH-004 domain models (in-memory / scaffold)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

RecheckRunStatus = Literal["succeeded", "partially_succeeded", "failed"]
CursorType = Literal["recheck"]
CandidateActiveStatus = Literal["active", "inactive", "unavailable", "excluded"]


@dataclass(frozen=True)
class ItemSeed:
    """Plan 入力となる既存 item（再確認対象候補）。"""

    source: str
    external_item_code: str
    item_id: str | None = None
    active_status: str = "active"
    last_checked_at: datetime | None = None
    popularity: float | None = None


@dataclass(frozen=True)
class FetchCursorRow:
    """fetch_cursor 走査単位（BATCH-004 は recheck のみ）。"""

    cursor_type: CursorType = "recheck"
    cursor_id: str | None = None
    target_external_genre_id: str | None = None
    scope: dict[str, Any] = field(default_factory=dict)
    page: int = 1
    cursor_status: str = "active"
    scope_fingerprint: str | None = None


@dataclass(frozen=True)
class RecheckPlan:
    """本 Run の再確認対象キュー（§9.2）。"""

    source: str
    items: tuple[ItemSeed, ...]
    hits: int


@dataclass(frozen=True)
class ResolvedCandidate:
    """IF-DB-BATCH-020 へ書く resolved 候補（§9.3）。"""

    batch_run_id: str
    source: str
    external_item_code: str
    candidate_active_status: CandidateActiveStatus
    reason_code: str
    detection_basis: str
    candidate_status: str = "detected"
    item_id: str | None = None
    raw_metadata_id: str | None = None
    api_call_log_id: str | None = None
    detected_at: datetime | None = None
    applied_at: datetime | None = None


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
class ItemRecheckSyncResult:
    """BATCH-004 Run 結果サマリ。"""

    batch_id: str
    job_run_id: str
    status: RecheckRunStatus = "failed"
    planned_item_count: int = 0
    succeeded_item_codes: list[str] = field(default_factory=list)
    failed_item_codes: list[str] = field(default_factory=list)
    raw_save_success_count: int = 0
    candidate_upsert_count: int = 0
    empty_hit_count: int = 0
    availability_zero_count: int = 0
    completed_phases: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
    # Item / Staging を作っていないことの検証用（常に空であるべき）
    created_items: list[dict[str, object]] = field(default_factory=list)
    created_staging: list[dict[str, object]] = field(default_factory=list)
    updated_item_rows: list[dict[str, object]] = field(default_factory=list)
