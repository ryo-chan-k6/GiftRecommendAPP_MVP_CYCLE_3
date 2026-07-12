"""Semantic extraction domain types (MOD-RECO-004 / user_semantic §5.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExtractedSemanticConcept:
    """Single extracted Semantic Concept for a recommendation run."""

    concept_code: str
    confidence: float
    input_intent: str
    extraction_method: str
    source_type: str
    assertion_polarity: str = "asserted"
    evidence_texts: tuple[str, ...] = ()

    def to_json_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "concept_code": self.concept_code,
            "confidence": self.confidence,
            "input_intent": self.input_intent,
            "assertion_polarity": self.assertion_polarity,
            "extraction_method": self.extraction_method,
            "source_type": self.source_type,
        }
        if self.evidence_texts:
            payload["evidence_texts"] = list(self.evidence_texts)
        return payload


@dataclass(frozen=True)
class HardFilterCandidate:
    """Hard Filter candidate separated from ng_condition (MOD-RECO-004 §8.3.5)."""

    filter_type: str
    filter_value: str
    evidence_text: str
    confidence: float
    source_type: str
    status: str = "candidate"


@dataclass(frozen=True)
class SemanticExtractionResult:
    """In-memory extraction outcome attached to execution_context."""

    concepts: tuple[ExtractedSemanticConcept, ...]
    hard_filter_candidates: tuple[HardFilterCandidate, ...]
    user_semantic_id: str
    semantic_config_version_id: str

    def to_extracted_semantic_json(self) -> dict[str, Any]:
        return {
            "concepts": [concept.to_json_dict() for concept in self.concepts],
        }
