"""Domain types for MOD-RECO-026 Item Semantic Generator."""

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
class ItemSemanticGenerationContext:
    """Batch generation context (distinct from Orchestrator execution_context)."""

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
class ItemSemanticGenerationResult:
    """Single-item generation outcome returned to Batch."""

    status: GenerationStatus
    semantic_json: dict[str, Any] | None = None
    item_semantic_id: str | None = None
    skip_reason: str | None = None


@dataclass(frozen=True)
class SemanticConceptRecord:
    concept_code: str
    semantic_config_version_id: str
    is_active: bool = True


@dataclass(frozen=True)
class SemanticRuleRecord:
    semantic_config_version_id: str
    rule_type: str
    match_value: str
    concept_code: str
    confidence: float
    source_types: tuple[str, ...] = ()
    input_intent: str = "neutral"


@dataclass(frozen=True)
class ItemSemanticRecord:
    item_semantic_id: str
    item_id: str
    semantic_config_version_id: str
    semantic_json: dict[str, Any]
    semantic_input_hash: str | None = None
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class TextSegment:
    """Normalized item text fragment for rule / LLM extraction."""

    text: str
    source_type: str
    input_intent: str = "neutral"
    is_keyword: bool = False
    assertion_polarity: str = "asserted"
