"""BATCH-014 domain models (in-memory / scaffold).

Embedding入力hash算出。item_embedding へは書込せず（BATCH-015 責務）、
embedding_input_hash / item_text_context を handoff（IF-DB-BATCH-015）する。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

EmbeddingInputHashRunStatus = Literal["succeeded", "partially_succeeded", "failed"]
GenerationType = Literal["semantic", "feature", "embedding"]
QueueStatus = Literal["queued", "processing", "succeeded", "failed", "skipped"]

# MVP は embedding_source_type = item_text_context 固定
# （item_embedding_テーブル定義書 §5.5 / §11.1）
DEFAULT_EMBEDDING_SOURCE_TYPE = "item_text_context"


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
    # Excluded from hash (§9.2): price, review, etc. kept only for boundary tests
    price: int | None = None
    review_average: float | None = None
    review_count: int | None = None


@dataclass(frozen=True)
class ConfigResolveHint:
    """Embedding model version（model_type=embedding, is_current）と入力構築 version。"""

    model_version_id: str
    embedding_source_version: str
    embedding_source_type: str = DEFAULT_EMBEDDING_SOURCE_TYPE


@dataclass(frozen=True)
class EmbeddingHashHandoffRecord:
    """IF-DB-BATCH-015 handoff（専用テーブルなし・in-memory）。

    物理列 item_embedding.embedding_input_hash への書込は BATCH-015 が行う。
    """

    item_id: str
    item_generation_queue_id: str
    model_version_id: str
    embedding_source_type: str
    embedding_source_version: str
    embedding_input_hash: str
    item_text_context: dict[str, Any]


@dataclass(frozen=True)
class DigestionPlan:
    items: tuple[QueueRow, ...]
    source_filter: str
    max_items: int
    queue_batch_size: int
    non_target_skip_count: int = 0


@dataclass
class EmbeddingInputHashJobResult:
    batch_id: str
    job_run_id: str
    status: EmbeddingInputHashRunStatus = "failed"
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
    item_embedding_write_count: int = 0
    queue_insert_count: int = 0
    handoff_records: list[dict[str, object]] = field(default_factory=list)
