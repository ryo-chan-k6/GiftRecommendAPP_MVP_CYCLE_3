"""Domain types for MOD-RECO-027 Item Feature Generator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class GenerationStatus(StrEnum):
    GENERATED = "generated"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class ItemSemanticInput:
    """item_semantic row or equivalent DTO supplied by BATCH-012."""

    item_id: str
    semantic_config_version_id: str
    semantic_json: dict[str, Any]


@dataclass(frozen=True)
class ItemFeatureGenerationContext:
    """Batch generation context (distinct from Orchestrator execution_context)."""

    trace_id: str
    batch_run_id: str
    item_generation_queue_id: str
    item_id: str
    semantic_config_version_id: str
    feature_input_hash: str
    item_semantic: ItemSemanticInput
    item_name: str | None = None
    item_caption: str | None = None
    genre_name: str | None = None
    attributes: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    brand_name: str | None = None
    skip_if_unchanged: bool = True


@dataclass(frozen=True)
class ItemFeatureGenerationResult:
    """Single-item Feature raw generation outcome returned to Batch."""

    status: GenerationStatus
    features: dict[str, float] = field(default_factory=dict)
    feature_codes: tuple[str, ...] = ()
    feature_input_hash: str = ""
    feature_normalization_version_id: str = ""
    item_feature_ids: tuple[str, ...] = ()
    skip_reason: str | None = None


@dataclass(frozen=True)
class ConceptFeatureRuleRecord:
    """Single concept_feature_rule row (sparse seed compatible)."""

    concept_code: str
    feature_code: str
    feature_delta: float
    polarity: str
    is_active: bool = True


@dataclass(frozen=True)
class NormalizationBinding:
    """Active normalization_rule binding for a semantic_config_version."""

    feature_normalization_version_id: str


@dataclass(frozen=True)
class ItemFeatureUpsertRow:
    """Single item_feature UPSERT row (raw only; normalized stays NULL)."""

    item_id: str
    semantic_config_version_id: str
    feature_code: str
    feature_input_hash: str
    feature_normalization_version_id: str
    raw_feature_value: float
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class ItemFeatureRecord:
    """Persisted item_feature row used for skip detection."""

    item_feature_id: str
    item_id: str
    semantic_config_version_id: str
    feature_code: str
    feature_input_hash: str
    feature_normalization_version_id: str
    raw_feature_value: float | None
    normalized_feature_value: float | None = None
