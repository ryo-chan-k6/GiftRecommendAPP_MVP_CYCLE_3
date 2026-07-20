"""BATCH-015 Item Embedding生成 domain models (in-memory / scaffold).

物理書込 IF = IF-VEC-BATCH-001（item_embedding Upsert）。
外部呼出 IF = IF-EXT-005（Embedding API）。
IF-DB-BATCH-015 は BATCH-014 handoff 消費のみ（hash 再算出禁止）。

モジュール: MOD-BATCH-036（Generator）/ MOD-BATCH-037（Repository）。
MOD-BATCH-015（Existing Item Recheck Planner）と混同しない。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

ItemEmbeddingRunStatus = Literal["succeeded", "partially_succeeded", "failed"]
GenerationType = Literal["semantic", "feature", "embedding"]
QueueStatus = Literal["queued", "processing", "succeeded", "failed", "skipped"]
EmbeddingGenStatus = Literal["generated", "skipped", "failed"]

# MVP 固定（item_embedding_テーブル定義書 §17.1）
DEFAULT_EMBEDDING_SOURCE_TYPE = "item_text_context"
EMBEDDING_DIMENSION = 1536
MVP_EMBEDDING_MODEL_NAME = "text-embedding-3-small"


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


@dataclass(frozen=True)
class EmbeddingHashHandoff:
    """BATCH-014（IF-DB-BATCH-015）handoff 消費用レコード。

    hash / item_text_context は再算出せず検証して利用する。
    """

    item_id: str
    item_generation_queue_id: str
    model_version_id: str
    embedding_source_type: str
    embedding_source_version: str
    embedding_input_hash: str
    item_text_context: dict[str, Any]


@dataclass(frozen=True)
class ConfigResolveHint:
    """MOD-RECO-003 相当: model_type=embedding / is_current。"""

    model_version_id: str
    model_name: str = MVP_EMBEDDING_MODEL_NAME
    embedding_dimension: int = EMBEDDING_DIMENSION
    embedding_source_type: str = DEFAULT_EMBEDDING_SOURCE_TYPE


@dataclass(frozen=True)
class EmbeddingGenerationContext:
    """IF-EXT-005 入力（MOD-BATCH-036）。"""

    item_id: str
    item_generation_queue_id: str
    model_version_id: str
    model_name: str
    embedding_input_hash: str
    item_text_context: dict[str, Any]
    embedding_input_text: str
    embedding_source_type: str
    trace_id: str
    dimension: int = EMBEDDING_DIMENSION


@dataclass(frozen=True)
class EmbeddingGenerationResult:
    """IF-EXT-005 出力。ベクトル全文はログ禁止。"""

    status: EmbeddingGenStatus
    embedding_vector: tuple[float, ...] | None = None
    model_name: str | None = None
    dimension: int | None = None
    latency_ms: int | None = None
    skip_reason: str | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class ItemEmbeddingUpsertRow:
    """IF-VEC-BATCH-001 Upsert 行。"""

    item_id: str
    model_version_id: str
    embedding_source_type: str
    embedding_input_hash: str
    embedding_vector: tuple[float, ...]
    generated_at: datetime


@dataclass(frozen=True)
class DigestionPlan:
    items: tuple[QueueRow, ...]
    source_filter: str
    max_items: int
    queue_batch_size: int
    non_target_skip_count: int = 0


@dataclass
class ItemEmbeddingJobResult:
    batch_id: str
    job_run_id: str
    status: ItemEmbeddingRunStatus = "failed"
    completed_phases: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
    planned_queue_count: int = 0
    claimed_count: int = 0
    generated_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    claim_conflict_skip_count: int = 0
    non_target_skip_count: int = 0
    api_call_count: int = 0
    succeeded_queue_ids: list[str] = field(default_factory=list)
    skipped_queue_ids: list[str] = field(default_factory=list)
    failed_queue_ids: list[str] = field(default_factory=list)
    item_embedding_write_count: int = 0
    item_write_count: int = 0
    queue_insert_count: int = 0
    hash_recompute_count: int = 0
    distribution_metric_write_count: int = 0
