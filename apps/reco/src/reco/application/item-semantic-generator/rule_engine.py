"""Rule-based Semantic Concept extraction for MOD-RECO-026."""

from __future__ import annotations

import re
from dataclasses import replace

from reco.domain.semantic_extraction import ExtractedSemanticConcept

from .constants import (
    DEFAULT_EXTRACTION_METHOD,
    DEFAULT_INPUT_INTENT,
    NEGATION_REVIEW_MARKERS,
    SOURCE_TYPE_CONFIDENCE_ADJUSTMENTS,
)
from .models import ItemSemanticGenerationContext, SemanticConceptRecord, SemanticRuleRecord, TextSegment


def collect_text_segments(context: ItemSemanticGenerationContext) -> tuple[TextSegment, ...]:
    """Split item fields by source_type (Semanticルール定義書 §3.2)."""
    segments: list[TextSegment] = []

    if context.item_name and context.item_name.strip():
        segments.append(
            TextSegment(
                text=context.item_name.strip(),
                source_type="item_name",
                input_intent=DEFAULT_INPUT_INTENT,
            )
        )

    if context.item_caption and context.item_caption.strip():
        segments.append(
            TextSegment(
                text=context.item_caption.strip(),
                source_type="item_caption",
                input_intent=DEFAULT_INPUT_INTENT,
            )
        )

    if context.item_description and context.item_description.strip():
        segments.append(
            TextSegment(
                text=context.item_description.strip(),
                source_type="item_description",
                input_intent=DEFAULT_INPUT_INTENT,
            )
        )

    if context.genre_name and context.genre_name.strip():
        segments.append(
            TextSegment(
                text=context.genre_name.strip(),
                source_type="item_genre",
                input_intent=DEFAULT_INPUT_INTENT,
            )
        )

    for tag in context.tags:
        normalized = tag.strip()
        if normalized:
            segments.append(
                TextSegment(
                    text=normalized,
                    source_type="item_tag",
                    input_intent=DEFAULT_INPUT_INTENT,
                    is_keyword=True,
                )
            )

    for attribute in context.attributes:
        normalized = attribute.strip()
        if normalized:
            segments.append(
                TextSegment(
                    text=normalized,
                    source_type="item_tag",
                    input_intent=DEFAULT_INPUT_INTENT,
                    is_keyword=True,
                )
            )

    for review in context.review_texts:
        normalized = review.strip()
        if not normalized:
            continue
        polarity = detect_review_polarity(normalized)
        if polarity == "negated":
            continue
        segments.append(
            TextSegment(
                text=normalized,
                source_type="item_review",
                input_intent=DEFAULT_INPUT_INTENT,
                assertion_polarity=polarity,
            )
        )

    if context.brand_name and context.brand_name.strip():
        segments.append(
            TextSegment(
                text=context.brand_name.strip(),
                source_type="item_brand",
                input_intent=DEFAULT_INPUT_INTENT,
            )
        )

    return tuple(segments)


def detect_review_polarity(text: str) -> str:
    """Detect negation context for item_review (§8.3.3)."""
    if any(marker in text for marker in NEGATION_REVIEW_MARKERS):
        return "negated"
    return "asserted"


def apply_rules(
    segments: tuple[TextSegment, ...],
    *,
    rules: tuple[SemanticRuleRecord, ...],
    active_concepts: tuple[SemanticConceptRecord, ...],
) -> list[ExtractedSemanticConcept]:
    active_codes = {concept.concept_code for concept in active_concepts}
    candidates: list[ExtractedSemanticConcept] = []

    keyword_rules = [rule for rule in rules if rule.rule_type == "keyword"]
    phrase_rules = [rule for rule in rules if rule.rule_type == "phrase"]
    pattern_rules = [rule for rule in rules if rule.rule_type == "pattern"]

    for segment in segments:
        if segment.assertion_polarity == "negated":
            continue

        for rule in keyword_rules:
            candidate = _match_rule(rule, segment, active_codes)
            if candidate is not None:
                candidates.append(candidate)

        for rule in phrase_rules:
            candidate = _match_rule(rule, segment, active_codes)
            if candidate is not None:
                candidates.append(candidate)

        for rule in pattern_rules:
            candidate = _match_pattern_rule(rule, segment, active_codes)
            if candidate is not None:
                candidates.append(candidate)

    return candidates


def apply_source_type_confidence_adjustment(
    concepts: list[ExtractedSemanticConcept],
) -> list[ExtractedSemanticConcept]:
    adjusted: list[ExtractedSemanticConcept] = []
    for concept in concepts:
        delta = SOURCE_TYPE_CONFIDENCE_ADJUSTMENTS.get(concept.source_type, 0.0)
        adjusted.append(
            replace(
                concept,
                confidence=max(0.0, min(1.0, concept.confidence + delta)),
            )
        )
    return adjusted


def filter_by_confidence(
    concepts: list[ExtractedSemanticConcept],
    *,
    threshold: float,
) -> list[ExtractedSemanticConcept]:
    return [concept for concept in concepts if concept.confidence >= threshold]


def dedupe_by_concept_code(
    concepts: list[ExtractedSemanticConcept],
) -> tuple[ExtractedSemanticConcept, ...]:
    best: dict[str, ExtractedSemanticConcept] = {}
    for concept in concepts:
        existing = best.get(concept.concept_code)
        if existing is None or concept.confidence > existing.confidence:
            best[concept.concept_code] = concept
    return tuple(best.values())


def merge_concept_lists(
    *concept_lists: list[ExtractedSemanticConcept],
) -> list[ExtractedSemanticConcept]:
    merged: list[ExtractedSemanticConcept] = []
    for concepts in concept_lists:
        merged.extend(concepts)
    return merged


def with_extraction_method(
    concept: ExtractedSemanticConcept,
    extraction_method: str,
) -> ExtractedSemanticConcept:
    return replace(concept, extraction_method=extraction_method)


def _match_rule(
    rule: SemanticRuleRecord,
    segment: TextSegment,
    active_codes: set[str],
) -> ExtractedSemanticConcept | None:
    if not _rule_applies_to_segment(rule, segment):
        return None
    if rule.match_value not in segment.text:
        return None
    if rule.concept_code not in active_codes:
        return None
    return _concept_from_rule(rule, segment)


def _match_pattern_rule(
    rule: SemanticRuleRecord,
    segment: TextSegment,
    active_codes: set[str],
) -> ExtractedSemanticConcept | None:
    if not _rule_applies_to_segment(rule, segment):
        return None
    if re.search(rule.match_value, segment.text) is None:
        return None
    if rule.concept_code not in active_codes:
        return None
    return _concept_from_rule(rule, segment)


def _rule_applies_to_segment(rule: SemanticRuleRecord, segment: TextSegment) -> bool:
    if rule.source_types and segment.source_type not in rule.source_types:
        return False
    if segment.is_keyword and rule.rule_type != "keyword":
        return False
    return True


def _concept_from_rule(
    rule: SemanticRuleRecord,
    segment: TextSegment,
) -> ExtractedSemanticConcept:
    intent = rule.input_intent or segment.input_intent or DEFAULT_INPUT_INTENT
    method = (
        rule.rule_type
        if rule.rule_type in {"keyword", "phrase", "pattern"}
        else DEFAULT_EXTRACTION_METHOD
    )
    return ExtractedSemanticConcept(
        concept_code=rule.concept_code,
        confidence=rule.confidence,
        input_intent=intent,
        extraction_method=method,
        source_type=segment.source_type,
        assertion_polarity=segment.assertion_polarity,
        evidence_texts=(segment.text,),
    )
