"""BATCH-009 domain models (in-memory / scaffold)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

ItemGenerationQueueRunStatus = Literal["succeeded", "partially_succeeded", "failed"]
DiffStatus = Literal["new", "updated", "unchanged", "unavailable"]
GenerationType = Literal["semantic", "feature", "embedding"]
QueueStatus = Literal["queued", "processing", "succeeded", "failed", "skipped"]

ELIGIBLE_DIFF_STATUSES: frozenset[str] = frozenset({"new", "updated"})
ACTIVE_ITEM_STATUS = "active"


@dataclass(frozen=True)
class MeaningSnapshot:
    """Meaning-affecting columns for meaning_input_diff (§9.2.1)."""

    item_name: str | None = None
    item_caption: str | None = None
    catchcopy: str | None = None
    external_genre_id: str | None = None
    attribute_ids: tuple[str, ...] = ()
    tag_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ItemRow:
    """BATCH-007 反映済み item 行（読取のみ）."""

    item_id: str
    source: str
    external_item_code: str
    active_status: str
    is_active: bool
    normalized_hash: str | None = None
    item_name: str | None = None
    item_caption: str | None = None
    catchcopy: str | None = None
    external_genre_id: str | None = None
    attribute_ids: tuple[str, ...] = ()
    tag_ids: tuple[str, ...] = ()
    price: int | None = None
    item_url: str | None = None
    review_average: float | None = None
    review_count: int | None = None
    availability: int | None = None

    def meaning_snapshot(self) -> MeaningSnapshot:
        return MeaningSnapshot(
            item_name=self.item_name,
            item_caption=self.item_caption,
            catchcopy=self.catchcopy,
            external_genre_id=self.external_genre_id,
            attribute_ids=self.attribute_ids,
            tag_ids=self.tag_ids,
        )


@dataclass(frozen=True)
class ProductDiffRow:
    """product_diff_result 行（読取のみ）."""

    product_diff_result_id: str
    batch_run_id: str
    staging_item_id: str
    external_item_code: str
    diff_status: DiffStatus
    old_hash: str | None = None
    new_hash: str | None = None
    previous_meaning: MeaningSnapshot | None = None
    previous_price: int | None = None
    previous_item_url: str | None = None
    previous_review_average: float | None = None
    previous_review_count: int | None = None
    previous_availability: int | None = None
    config_version_only: bool = False
    feature_input_hash_only: bool = False
    embedding_only: bool = False


@dataclass(frozen=True)
class QueueRow:
    """item_generation_queue 行."""

    item_generation_queue_id: str
    item_id: str
    generation_type: GenerationType
    queue_status: QueueStatus
    retry_count: int
    queued_at: datetime


@dataclass(frozen=True)
class ConfigResolveHint:
    """Config Version Resolver stub output (§8.2 resolve_config)."""

    semantic_config_version_id: str


@dataclass(frozen=True)
class FeatureResolveHint:
    """Feature Input Candidate Resolver stub output (§8.2 resolve_feature)."""

    feature_input_hash: str | None = None


@dataclass(frozen=True)
class RegistrationPlan:
    """plan phase output."""

    items: tuple[ProductDiffRow, ...]
    source_filter: str
    max_items: int
    diff_batch_run_id: str | None
    unavailable_skip_count: int = 0
    unchanged_skip_count: int = 0


@dataclass(frozen=True)
class RegistrationDecision:
    """evaluate phase output for one item."""

    should_register: bool
    generation_type: GenerationType | None = None
    skip_reason: str | None = None
    meaning_input_diff: bool = False
    non_meaning_only: bool = False


@dataclass
class ItemGenerationQueueResult:
    """BATCH-009 Run 結果サマリ."""

    batch_id: str
    job_run_id: str
    status: ItemGenerationQueueRunStatus = "failed"
    planned_diff_count: int = 0
    completed_phases: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
    succeeded_external_codes: list[str] = field(default_factory=list)
    failed_external_codes: list[str] = field(default_factory=list)
    skipped_external_codes: list[str] = field(default_factory=list)
    queue_inserted_count: int = 0
    queue_queued_at_updated_count: int = 0
    queue_processing_skip_count: int = 0
    queue_inactive_skip_count: int = 0
    queue_non_meaning_skip_count: int = 0
    queue_unchanged_skip_count: int = 0
    queue_unavailable_skip_count: int = 0
    queue_semantic_count: int = 0
    queue_feature_count: int = 0
    queue_embedding_count: int = 0
    queue_register_failed_count: int = 0
    written_queue_rows: list[dict[str, object]] = field(default_factory=list)
    item_write_count: int = 0
    product_diff_write_count: int = 0
