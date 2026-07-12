"""LLM on-demand classification for MOD-RECO-004 (§8.3.4)."""

from __future__ import annotations

import json
from dataclasses import dataclass

from reco.domain.semantic_extraction import ExtractedSemanticConcept
from reco.infrastructure.external_ai.client import ExternalAiClient

from .constants import (
    CONFIDENCE_ADOPTION_THRESHOLD,
    CONFIDENCE_HIGH,
    CONFIDENCE_WEAK_MIN,
    DEFAULT_EXTRACTION_METHOD,
)
from .models import SemanticConceptRecord, TextSegment
from .rule_engine import filter_by_confidence


@dataclass(frozen=True)
class LlmExtractionRequest:
    segments: tuple[TextSegment, ...]
    relationship_code: str
    occasion_code: str


def should_invoke_llm(
    segments: tuple[TextSegment, ...],
    rule_concepts: list[ExtractedSemanticConcept],
) -> bool:
    adopted = filter_by_confidence(
        rule_concepts,
        threshold=CONFIDENCE_ADOPTION_THRESHOLD,
    )
    if not segments:
        return False

    if all(segment.is_keyword for segment in segments):
        if len(adopted) >= 2:
            return False
        max_confidence = max((concept.confidence for concept in adopted), default=0.0)
        if max_confidence >= CONFIDENCE_HIGH:
            return False
        return len(adopted) == 0

    has_free_text = any(segment.source_type == "free_text" for segment in segments)
    if has_free_text and not adopted:
        return True

    max_confidence = max((concept.confidence for concept in rule_concepts), default=0.0)
    if CONFIDENCE_WEAK_MIN <= max_confidence < CONFIDENCE_ADOPTION_THRESHOLD:
        return True

    return any(
        segment.source_type in {"preferred_condition", "non_preferred_condition"}
        and not segment.is_keyword
        and not _segment_has_rule_hit(segment, rule_concepts)
        for segment in segments
    )


def extract_with_llm(
    request: LlmExtractionRequest,
    *,
    client: ExternalAiClient,
    active_concepts: tuple[SemanticConceptRecord, ...],
) -> list[ExtractedSemanticConcept]:
    prompt = _build_prompt(request, active_concepts)
    response = client.generate(prompt, purpose="semantic_extraction")
    return _parse_llm_response(response.text, active_concepts=active_concepts)


def _segment_has_rule_hit(
    segment: TextSegment,
    rule_concepts: list[ExtractedSemanticConcept],
) -> bool:
    return any(concept.source_type == segment.source_type for concept in rule_concepts)


def _build_prompt(
    request: LlmExtractionRequest,
    active_concepts: tuple[SemanticConceptRecord, ...],
) -> str:
    concept_codes = [concept.concept_code for concept in active_concepts]
    lines = [
        "Extract semantic concepts from user gift preference text.",
        f"relationship_code={request.relationship_code}",
        f"occasion_code={request.occasion_code}",
        f"allowed_concept_codes={json.dumps(concept_codes, ensure_ascii=False)}",
        "segments:",
    ]
    for segment in request.segments:
        lines.append(
            json.dumps(
                {
                    "text": segment.text,
                    "source_type": segment.source_type,
                    "input_intent": segment.input_intent,
                },
                ensure_ascii=False,
            )
        )
    lines.append(
        'Return JSON: {"concepts":[{"concept_code":"...","confidence":0.0,'
        '"input_intent":"prefer|avoid|neutral","evidence_texts":["..."]}]}'
    )
    return "\n".join(lines)


def _parse_llm_response(
    text: str,
    *,
    active_concepts: tuple[SemanticConceptRecord, ...],
) -> list[ExtractedSemanticConcept]:
    active_codes = {concept.concept_code for concept in active_concepts}
    payload = _load_json_payload(text)
    if payload is None:
        return []

    raw_concepts = payload.get("concepts", [])
    if not isinstance(raw_concepts, list):
        return []

    concepts: list[ExtractedSemanticConcept] = []
    for item in raw_concepts:
        if not isinstance(item, dict):
            continue
        concept_code = item.get("concept_code")
        confidence = item.get("confidence")
        if not isinstance(concept_code, str) or concept_code not in active_codes:
            continue
        if not isinstance(confidence, (int, float)):
            continue
        input_intent = item.get("input_intent", "neutral")
        if not isinstance(input_intent, str):
            input_intent = "neutral"
        evidence = item.get("evidence_texts", [])
        evidence_texts: tuple[str, ...] = ()
        if isinstance(evidence, list):
            evidence_texts = tuple(str(value) for value in evidence if str(value).strip())
        concepts.append(
            ExtractedSemanticConcept(
                concept_code=concept_code,
                confidence=float(confidence),
                input_intent=input_intent,
                extraction_method="llm",
                source_type="free_text",
                evidence_texts=evidence_texts,
            )
        )
    return concepts


def _load_json_payload(text: str) -> dict[str, object] | None:
    stripped = text.strip()
    if not stripped:
        return None
    if stripped.startswith("{"):
        try:
            loaded = json.loads(stripped)
        except json.JSONDecodeError:
            return None
        return loaded if isinstance(loaded, dict) else None
    return None
