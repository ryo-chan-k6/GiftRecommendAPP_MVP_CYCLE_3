"""Rule-based Semantic Concept extraction for MOD-RECO-004."""

from __future__ import annotations

import re
from dataclasses import replace

from reco.domain.semantic_extraction import ExtractedSemanticConcept

from .constants import DEFAULT_EXTRACTION_METHOD
from .models import SemanticConceptRecord, SemanticRuleRecord, TextSegment


def collect_text_segments(request) -> tuple[TextSegment, ...]:
    """Collect preferred / non_preferred / free_text segments (ng excluded)."""
    segments: list[TextSegment] = []

    preferred = request.preferred_condition
    if preferred is not None:
        if preferred.preferred_text and preferred.preferred_text.strip():
            segments.append(
                TextSegment(
                    text=preferred.preferred_text.strip(),
                    source_type="preferred_condition",
                    input_intent="prefer",
                )
            )
        for keyword in preferred.preferred_keywords:
            normalized = keyword.strip()
            if normalized:
                segments.append(
                    TextSegment(
                        text=normalized,
                        source_type="preferred_condition",
                        input_intent="prefer",
                        is_keyword=True,
                    )
                )

    non_preferred = request.non_preferred_condition
    if non_preferred is not None:
        if non_preferred.non_preferred_text and non_preferred.non_preferred_text.strip():
            segments.append(
                TextSegment(
                    text=non_preferred.non_preferred_text.strip(),
                    source_type="non_preferred_condition",
                    input_intent="avoid",
                )
            )
        for keyword in non_preferred.non_preferred_keywords:
            normalized = keyword.strip()
            if normalized:
                segments.append(
                    TextSegment(
                        text=normalized,
                        source_type="non_preferred_condition",
                        input_intent="avoid",
                        is_keyword=True,
                    )
                )

    if request.free_text and request.free_text.strip():
        segments.append(
            TextSegment(
                text=request.free_text.strip(),
                source_type="free_text",
                input_intent="neutral",
            )
        )

    return tuple(segments)


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
        for rule in keyword_rules:
            if not _rule_applies_to_segment(rule, segment):
                continue
            if rule.match_value not in segment.text:
                continue
            if rule.concept_code not in active_codes:
                continue
            candidates.append(_concept_from_rule(rule, segment))

        for rule in phrase_rules:
            if not _rule_applies_to_segment(rule, segment):
                continue
            if rule.match_value not in segment.text:
                continue
            if rule.concept_code not in active_codes:
                continue
            candidates.append(_concept_from_rule(rule, segment))

        for rule in pattern_rules:
            if not _rule_applies_to_segment(rule, segment):
                continue
            if re.search(rule.match_value, segment.text) is None:
                continue
            if rule.concept_code not in active_codes:
                continue
            candidates.append(_concept_from_rule(rule, segment))

    return candidates


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
    intent = rule.input_intent or segment.input_intent
    method = rule.rule_type if rule.rule_type in {"keyword", "phrase", "pattern"} else DEFAULT_EXTRACTION_METHOD
    return ExtractedSemanticConcept(
        concept_code=rule.concept_code,
        confidence=rule.confidence,
        input_intent=intent,
        extraction_method=method,
        source_type=segment.source_type,
        evidence_texts=(segment.text,),
    )


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
