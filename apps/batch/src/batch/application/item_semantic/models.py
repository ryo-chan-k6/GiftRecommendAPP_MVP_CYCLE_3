"""BATCH-010 domain models (in-memory / scaffold)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

ItemSemanticRunStatus = Literal["succeeded", "partially_succeeded", "failed"]
GenerationType = Literal["semantic", "feature", "embedding"]
QueueStatus = Literal["queued", "processing", "succeeded", "failed", "skipped"]
SemanticGenStatus = Literal["generated", "skipped", "failed"]

CLAIMABLE_GENERATION_TYPE: GenerationType = "semantic"
CLAIMABLE_QUEUE_STATUS: QueueStatus = "queued"


@dataclass(frozen=True)
class QueueRow:
    """item_generation_queue 行（消化対象）。"""

    item_generation_queue_id: str
    item_id: str
    generation_type: GenerationType
    queue_status: QueueStatus
    retry_count: int = 0
    queued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class ItemContext:
    """Semantic 生成用 Item コンテキスト（読取のみ）。"""

    item_id: str
    source: str
    external_item_code: str
    active_status: str
    is_active: bool
    item_name: str | None = None
    item_caption: str | None = None
    item_description: str | None = None
    genre_name: str | None = None
    attributes: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    brand_name: str | None = None
    review_texts: tuple[str, ...] = ()


@dataclass(frozen=True)
class ItemSemanticRow:
    """item_semantic 既存行（skip 判定用）。"""

    item_semantic_id: str
    item_id: str
    semantic_config_version_id: str
    semantic_json: dict[str, Any]
    semantic_input_hash: str | None = None


@dataclass(frozen=True)
class ConfigResolveHint:
    """Config Version Resolver stub output (§8.2 resolve_config)."""

    semantic_config_version_id: str


@dataclass(frozen=True)
class SemanticGenerationContext:
    """IF-SHARED-001 入力（MOD-RECO-026 context 相当）。"""

    trace_id: str
    batch_run_id: str
    item_generation_queue_id: str
    item_id: str
    semantic_config_version_id: str
    item_name: str | None = None
    item_caption: str | None = None
    item_description: str | None = None
    genre_name: str | None = None
    attributes: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    review_texts: tuple[str, ...] = ()
    brand_name: str | None = None
    skip_if_unchanged: bool = True


@dataclass(frozen=True)
class SemanticGenerationResult:
    """IF-SHARED-001 出力（MOD-RECO-026 result 相当）。"""

    status: SemanticGenStatus
    semantic_json: dict[str, Any] | None = None
    item_semantic_id: str | None = None
    skip_reason: str | None = None
    semantic_input_hash: str | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class DigestionPlan:
    """plan Phase 出力。"""

    items: tuple[QueueRow, ...]
    source_filter: str
    max_items: int
    queue_batch_size: int
    non_semantic_skip_count: int = 0


@dataclass
class ItemSemanticJobResult:
    """BATCH-010 Run 結果。"""

    batch_id: str
    job_run_id: str
    status: ItemSemanticRunStatus = "failed"
    completed_phases: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
    planned_queue_count: int = 0
    claimed_count: int = 0
    semantic_generated_count: int = 0
    semantic_skipped_count: int = 0
    semantic_failed_count: int = 0
    claim_conflict_skip_count: int = 0
    non_semantic_skip_count: int = 0
    succeeded_queue_ids: list[str] = field(default_factory=list)
    skipped_queue_ids: list[str] = field(default_factory=list)
    failed_queue_ids: list[str] = field(default_factory=list)
    item_write_count: int = 0
    queue_insert_count: int = 0
    written_item_semantic_rows: list[dict[str, object]] = field(default_factory=list)
