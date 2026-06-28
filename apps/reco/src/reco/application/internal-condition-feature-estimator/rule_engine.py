"""Rule lookup and internal condition delta aggregation for MOD-RECO-006."""

from __future__ import annotations

from collections.abc import Callable

from reco.domain.gift_meaning.features import MVP_FEATURE_CODES
from reco.domain.semantic_extraction import ExtractedSemanticConcept

from .constants import (
    CONFIDENCE_THRESHOLD,
    DEFAULT_FREE_TEXT_WEIGHT,
    INTERNAL_SOURCE_TYPES,
    POLARITY_MIXED,
    POLARITY_NEGATIVE,
    POLARITY_POSITIVE,
)
from .errors import InternalFeatureEstimateError
from .models import ConceptFeatureRuleRecord, InternalFeatureIntegrationWeights


def zero_feature_vector() -> dict[str, float]:
    return {code: 0.0 for code in MVP_FEATURE_CODES}


def resolve_polarity_sign(polarity: str, input_intent: str) -> float:
    """Featureルール定義書 §8.3.1.1 / enum定義書 §6.22."""
    if polarity == POLARITY_POSITIVE:
        return 1.0
    if polarity == POLARITY_NEGATIVE:
        return -1.0
    if polarity == POLARITY_MIXED:
        if input_intent == "avoid":
            return -1.0
        return 1.0
    raise InternalFeatureEstimateError(f"unknown concept_feature_rule polarity: {polarity}")


def apply_non_preferred_inversion(polarity: str) -> float:
    """§11.3 反転。mixed 行は input_intent 基準で符号化済みのため二重反転しない。"""
    if polarity == POLARITY_MIXED:
        return 1.0
    return -1.0


def compute_axis_effective_delta(
    rule: ConceptFeatureRuleRecord,
    *,
    confidence: float,
    input_intent: str,
    source_type: str,
    free_text_weight: float = DEFAULT_FREE_TEXT_WEIGHT,
) -> float:
    """§8.3.1: feature_delta * polarity_sign * confidence, then source-type weight."""
    polarity_sign = resolve_polarity_sign(rule.polarity, input_intent)
    base_delta = rule.feature_delta * polarity_sign * confidence

    if source_type == "preferred_condition":
        return base_delta
    if source_type == "non_preferred_condition":
        return base_delta * apply_non_preferred_inversion(rule.polarity)
    if source_type == "free_text":
        return base_delta * free_text_weight
    return 0.0


def is_internal_condition_concept(concept: ExtractedSemanticConcept) -> bool:
    return concept.source_type in INTERNAL_SOURCE_TYPES


def should_apply_concept(concept: ExtractedSemanticConcept) -> bool:
    return concept.confidence >= CONFIDENCE_THRESHOLD


def aggregate_concept_deltas(
    concepts: tuple[ExtractedSemanticConcept, ...],
    *,
    lookup_rules: Callable[[str], tuple[ConceptFeatureRuleRecord, ...]],
    integration_weights: InternalFeatureIntegrationWeights | None = None,
) -> tuple[dict[str, float], dict[str, float], dict[str, float], int]:
    """Return preferred/avoid/free_text deltas and applied concept count."""
    preferred_delta = zero_feature_vector()
    avoid_delta = zero_feature_vector()
    free_text_delta = zero_feature_vector()
    free_text_weight = (
        integration_weights.free_text_weight
        if integration_weights is not None
        else DEFAULT_FREE_TEXT_WEIGHT
    )
    applied_concept_count = 0

    for concept in concepts:
        if not is_internal_condition_concept(concept):
            continue
        if not should_apply_concept(concept):
            continue

        rules = lookup_rules(concept.concept_code)
        applied_concept_count += 1
        if not rules:
            continue

        target = _target_delta_for_source_type(
            concept.source_type,
            preferred_delta,
            avoid_delta,
            free_text_delta,
        )
        for rule in rules:
            if rule.feature_code not in MVP_FEATURE_CODES:
                continue
            effective = compute_axis_effective_delta(
                rule,
                confidence=concept.confidence,
                input_intent=concept.input_intent,
                source_type=concept.source_type,
                free_text_weight=free_text_weight,
            )
            target[rule.feature_code] += effective

    return preferred_delta, avoid_delta, free_text_delta, applied_concept_count


def merge_internal_feature_delta(
    preferred_delta: dict[str, float],
    avoid_delta: dict[str, float],
    free_text_delta: dict[str, float],
    *,
    weights: InternalFeatureIntegrationWeights | None = None,
) -> dict[str, float]:
    """Featureルール定義書 §12.2."""
    preferred_weight = weights.preferred_weight if weights is not None else 1.0
    avoid_weight = weights.avoid_weight if weights is not None else 1.0
    return {
        axis: (
            preferred_weight * preferred_delta[axis]
            + avoid_weight * avoid_delta[axis]
            + free_text_delta[axis]
        )
        for axis in MVP_FEATURE_CODES
    }


def _target_delta_for_source_type(
    source_type: str,
    preferred_delta: dict[str, float],
    avoid_delta: dict[str, float],
    free_text_delta: dict[str, float],
) -> dict[str, float]:
    if source_type == "preferred_condition":
        return preferred_delta
    if source_type == "non_preferred_condition":
        return avoid_delta
    if source_type == "free_text":
        return free_text_delta
    raise InternalFeatureEstimateError(
        f"unsupported internal condition source_type: {source_type}",
    )
