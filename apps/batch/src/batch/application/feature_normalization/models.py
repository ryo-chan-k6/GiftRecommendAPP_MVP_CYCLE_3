"""BATCH-013 Feature正規化 domain models (in-memory / scaffold)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

FeatureNormalizationRunStatus = Literal["succeeded", "partially_succeeded", "failed"]
GenerationType = Literal["semantic", "feature", "embedding"]
QueueStatus = Literal["queued", "processing", "succeeded", "failed", "skipped"]
NormalizationStatus = Literal["normalized", "skipped", "failed"]


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
class RawFeatureAxis:
    """BATCH-012（IF-DB-BATCH-013）が生成した raw 8 軸の 1 行（読取専用入力）。"""

    feature_code: str
    feature_input_hash: str
    feature_normalization_version_id: str
    raw_feature_value: float


@dataclass(frozen=True)
class ConfigResolveHint:
    semantic_config_version_id: str
    feature_normalization_version_id: str


@dataclass(frozen=True)
class NormalizationParams:
    """feature_normalization_version.parameter_json（MVP 固定 sigmoid）。"""

    normalization_method: str = "sigmoid"
    center_feature: float = 0.5
    k_feature: float = 4.0


@dataclass(frozen=True)
class NormalizeContext:
    """IF-SHARED-003 で MOD-BATCH-034 へ渡す正規化コンテキスト。"""

    item_id: str
    semantic_config_version_id: str
    feature_input_hash: str
    feature_normalization_version_id: str
    params: NormalizationParams
    raw_axes: tuple[RawFeatureAxis, ...]
    trace_id: str


@dataclass(frozen=True)
class NormalizedAxisValue:
    feature_code: str
    normalized_feature_value: float


@dataclass(frozen=True)
class NormalizationResult:
    """MOD-BATCH-034 の正規化結果（normalized のみ・raw は不変）。"""

    status: NormalizationStatus
    normalized: tuple[NormalizedAxisValue, ...] = ()
    feature_normalization_version_id: str | None = None
    feature_input_hash: str | None = None
    axis_count: int = 0
    saturate_count: int = 0
    skip_reason: str | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class ItemFeatureNormalizedUpdateRow:
    """IF-DB-BATCH-014: item_feature.normalized_feature_value の UPDATE 対象 1 軸。"""

    item_id: str
    semantic_config_version_id: str
    feature_code: str
    feature_input_hash: str
    feature_normalization_version_id: str
    normalized_feature_value: float


@dataclass(frozen=True)
class MeaningProjection:
    """normalized 8 軸から算出した Social / Symbolic 射影。"""

    item_social: float
    item_symbolic: float


@dataclass(frozen=True)
class ItemMeaningUpsertRow:
    """IF-DB-BATCH-014: item_meaning の UPSERT 対象。"""

    item_id: str
    semantic_config_version_id: str
    item_social: float
    item_symbolic: float
    generated_at: datetime


@dataclass(frozen=True)
class DigestionPlan:
    items: tuple[QueueRow, ...]
    source_filter: str
    max_items: int
    queue_batch_size: int
    non_target_skip_count: int = 0


@dataclass
class FeatureNormalizationJobResult:
    batch_id: str
    job_run_id: str
    status: FeatureNormalizationRunStatus = "failed"
    completed_phases: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
    planned_queue_count: int = 0
    normalized_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    claim_conflict_skip_count: int = 0
    non_target_skip_count: int = 0
    saturate_count: int = 0
    succeeded_queue_ids: list[str] = field(default_factory=list)
    skipped_queue_ids: list[str] = field(default_factory=list)
    failed_queue_ids: list[str] = field(default_factory=list)
    item_feature_normalized_update_count: int = 0
    item_meaning_upsert_count: int = 0
    item_feature_raw_write_count: int = 0
    item_semantic_write_count: int = 0
    queue_insert_count: int = 0
    normalization_distribution_metric_write_count: int = 0
