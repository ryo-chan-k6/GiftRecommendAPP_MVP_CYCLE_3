"""LLM on-demand classification for MOD-RECO-026 (§8.3.4)."""

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
    DEFAULT_INPUT_INTENT,
)
from .models import ItemSemanticGenerationContext, SemanticConceptRecord, TextSegment
from .rule_engine import filter_by_confidence


@dataclass(frozen=True)
class LlmExtractionRequest:
    segments: tuple[TextSegment, ...]
    item_id: str


def should_invoke_llm(
    context: ItemSemanticGenerationContext,
    segments: tuple[TextSegment, ...],
    rule_concepts: list[ExtractedSemanticConcept],
) -> bool:
    adopted = filter_by_confidence(
        rule_concepts,
        threshold=CONFIDENCE_ADOPTION_THRESHOLD,
    )
    if not segments:
        return False

    if len(adopted) >= 2:
        return False

    max_confidence = max((concept.confidence for concept in adopted), default=0.0)
    if max_confidence >= CONFIDENCE_HIGH:
        return False

    has_description = bool(context.item_description and context.item_description.strip())
    has_caption = bool(context.item_caption and context.item_caption.strip())
    if (has_description or has_caption) and not adopted:
        return True

    raw_max = max((concept.confidence for concept in rule_concepts), default=0.0)
    if CONFIDENCE_WEAK_MIN <= raw_max < CONFIDENCE_ADOPTION_THRESHOLD and has_description:
        return True

    only_name = (
        has_name_only_context(context)
        and not adopted
        and _looks_like_natural_sentence(context.item_name or "")
    )
    if only_name:
        return True

    if all(segment.source_type in {"item_tag", "item_genre"} for segment in segments):
        return False

    return False


def has_name_only_context(context: ItemSemanticGenerationContext) -> bool:
    return bool(context.item_name and context.item_name.strip()) and not any(
        [
            context.item_description and context.item_description.strip(),
            context.item_caption and context.item_caption.strip(),
        ]
    )


def extract_with_llm(
    request: LlmExtractionRequest,
    *,
    client: ExternalAiClient,
    active_concepts: tuple[SemanticConceptRecord, ...],
) -> list[ExtractedSemanticConcept]:
    prompt = _build_prompt(request, active_concepts)
    response = client.generate(prompt, purpose="item_semantic_extraction")
    return _parse_llm_response(response.text, active_concepts=active_concepts)


def _looks_like_natural_sentence(text: str) -> bool:
    normalized = text.strip()
    if len(normalized) < 8:
        return False
    return any(marker in normalized for marker in ("の", "を", "が", "に", "で", "と"))


def _build_prompt(
    request: LlmExtractionRequest,
    active_concepts: tuple[SemanticConceptRecord, ...],
) -> str:
    concept_codes = [concept.concept_code for concept in active_concepts]
    lines = [
        "Extract semantic concepts from item product text.",
        f"item_id={request.item_id}",
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
        '"input_intent":"neutral","evidence_texts":["..."]}]}'
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
        input_intent = item.get("input_intent", DEFAULT_INPUT_INTENT)
        if not isinstance(input_intent, str):
            input_intent = DEFAULT_INPUT_INTENT
        evidence = item.get("evidence_texts", [])
        evidence_texts: tuple[str, ...] = ()
        if isinstance(evidence, list):
            evidence_texts = tuple(str(value) for value in evidence if str(value).strip())
        source_type = item.get("source_type", "item_description")
        if not isinstance(source_type, str):
            source_type = "item_description"
        concepts.append(
            ExtractedSemanticConcept(
                concept_code=concept_code,
                confidence=float(confidence),
                input_intent=input_intent,
                extraction_method="llm",
                source_type=source_type,
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
