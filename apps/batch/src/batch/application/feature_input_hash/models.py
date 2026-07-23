"""BATCH-011 domain models (in-memory / scaffold)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

FeatureInputHashRunStatus = Literal["succeeded", "partially_succeeded", "failed"]
GenerationType = Literal["semantic", "feature", "embedding"]
QueueStatus = Literal["queued", "processing", "succeeded", "failed", "skipped"]


@dataclass(frozen=True)
class QueueRow:
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
class ItemRow:
    item_id: str
    source: str
    external_item_code: str
    active_status: str = "active"
    is_active: bool = True
    item_name: str | None = None
    catchcopy: str | None = None
    item_caption: str | None = None
    genre_id: str | None = None
    genre_name: str | None = None
    attributes: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    # Excluded from hash (§13.3): price, review, etc. kept only for boundary tests
    price: int | None = None
    review_average: float | None = None
    review_count: int | None = None


@dataclass(frozen=True)
class ItemSemanticRow:
    item_id: str
    semantic_config_version_id: str
    semantic_json: dict[str, Any]


@dataclass(frozen=True)
class ConfigResolveHint:
    semantic_config_version_id: str


@dataclass(frozen=True)
class HashHandoffRecord:
    """IF-DB-BATCH-012 中間永続（item_feature_input）向け handoff レコード。"""

    item_id: str
    item_generation_queue_id: str
    semantic_config_version_id: str
    feature_input_hash: str
    feature_input_payload: dict[str, Any]


@dataclass(frozen=True)
class DigestionPlan:
    items: tuple[QueueRow, ...]
    source_filter: str
    max_items: int
    queue_batch_size: int
    non_target_skip_count: int = 0


@dataclass
class FeatureInputHashJobResult:
    batch_id: str
    job_run_id: str
    status: FeatureInputHashRunStatus = "failed"
    completed_phases: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
    planned_queue_count: int = 0
    hashed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    claim_conflict_skip_count: int = 0
    non_target_skip_count: int = 0
    succeeded_queue_ids: list[str] = field(default_factory=list)
    skipped_queue_ids: list[str] = field(default_factory=list)
    failed_queue_ids: list[str] = field(default_factory=list)
    item_write_count: int = 0
    item_semantic_write_count: int = 0
    item_feature_write_count: int = 0
    queue_insert_count: int = 0
    handoff_records: list[dict[str, object]] = field(default_factory=list)
