"""Repository record types for MOD-RECO-004."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


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
    input_intent: str = "prefer"


@dataclass(frozen=True)
class UserSemanticRecord:
    user_semantic_id: str
    recommendation_run_id: str
    semantic_config_version_id: str
    extracted_semantic_json: dict[str, object]
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class TextSegment:
    """Normalized user input fragment for rule / LLM extraction."""

    text: str
    source_type: str
    input_intent: str
    is_keyword: bool = False
