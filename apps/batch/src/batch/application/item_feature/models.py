"""BATCH-012 Item Feature生成 domain models (in-memory / scaffold)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

ItemFeatureRunStatus = Literal["succeeded", "partially_succeeded", "failed"]
GenerationType = Literal["semantic", "feature", "embedding"]
QueueStatus = Literal["queued", "processing", "succeeded", "failed", "skipped"]
FeatureGenerationStatus = Literal["generated", "skipped", "failed"]


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
    genre_id: str | None = None
    genre_name: str | None = None


@dataclass(frozen=True)
class ItemSemanticRow:
    item_id: str
    semantic_config_version_id: str
    semantic_json: dict[str, Any]


@dataclass(frozen=True)
class FeatureInputHashHandoff:
    """BATCH-011（IF-DB-BATCH-012）から引き渡される feature_input_hash。"""

    item_id: str
    semantic_config_version_id: str
    feature_input_hash: str


@dataclass(frozen=True)
class ConfigResolveHint:
    semantic_config_version_id: str
    feature_normalization_version_id: str


@dataclass(frozen=True)
class ConceptRef:
    """item_semantic.semantic_json.concepts[] から抽出した生成入力。"""

    concept_code: str
    confidence: float = 1.0
    source_weight: float = 1.0


@dataclass(frozen=True)
class FeatureGenerationContext:
    """IF-SHARED-002 で MOD-RECO-027 へ渡す生成コンテキスト。"""

    item_id: str
    semantic_config_version_id: str
    feature_input_hash: str
    feature_normalization_version_id: str
    concepts: tuple[ConceptRef, ...]
    trace_id: str


@dataclass(frozen=True)
class FeatureAxisValue:
    feature_code: str
    raw_feature_value: float


@dataclass(frozen=True)
class FeatureGenerationResult:
    """MOD-RECO-027 の生成結果（raw のみ・normalized は BATCH-013）。"""

    status: FeatureGenerationStatus
    features: tuple[FeatureAxisValue, ...] = ()
    feature_normalization_version_id: str | None = None
    feature_input_hash: str | None = None
    concept_count: int = 0
    rule_hit_count: int = 0
    raw_clip_count: int = 0
    skip_reason: str | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class ItemFeatureUpsertRow:
    """IF-DB-BATCH-013 で item_feature へ Upsert する 1 軸分の行。"""

    item_id: str
    semantic_config_version_id: str
    feature_code: str
    feature_input_hash: str
    feature_normalization_version_id: str
    raw_feature_value: float
    generated_at: datetime


@dataclass(frozen=True)
class DigestionPlan:
    items: tuple[QueueRow, ...]
    source_filter: str
    max_items: int
    queue_batch_size: int
    non_target_skip_count: int = 0


@dataclass
class ItemFeatureJobResult:
    batch_id: str
    job_run_id: str
    status: ItemFeatureRunStatus = "failed"
    completed_phases: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
    planned_queue_count: int = 0
    generated_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    claim_conflict_skip_count: int = 0
    non_target_skip_count: int = 0
    raw_clip_count: int = 0
    succeeded_queue_ids: list[str] = field(default_factory=list)
    skipped_queue_ids: list[str] = field(default_factory=list)
    failed_queue_ids: list[str] = field(default_factory=list)
    item_feature_write_count: int = 0
    item_semantic_write_count: int = 0
    queue_insert_count: int = 0
