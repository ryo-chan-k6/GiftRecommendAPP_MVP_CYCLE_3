"""Item Feature delta aggregation for MOD-RECO-027."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from reco.domain.gift_meaning.features import MVP_FEATURE_CODES
from reco.domain.semantic_extraction import ExtractedSemanticConcept

from .constants import (
    NEUTRAL_BASE,
    POLARITY_MIXED,
    POLARITY_NEGATIVE,
    POLARITY_POSITIVE,
    SOURCE_WEIGHT_BY_TYPE,
)
from .errors import ItemFeatureGeneratorError
from .models import ConceptFeatureRuleRecord


def zero_feature_vector() -> dict[str, float]:
    return {code: 0.0 for code in MVP_FEATURE_CODES}


def neutral_feature_base() -> dict[str, float]:
    return {code: NEUTRAL_BASE for code in MVP_FEATURE_CODES}


def resolve_source_weight(source_type: str) -> float:
    """Featureルール定義書 §13.2 source_weight。"""
    weight = SOURCE_WEIGHT_BY_TYPE.get(source_type)
    if weight is None:
        return 0.0
    return weight


def apply_polarity(feature_delta: float, polarity: str) -> float:
    """concept_feature_rule.polarity を delta 符号へ反映する。"""
    if polarity == POLARITY_POSITIVE:
        return feature_delta
    if polarity == POLARITY_NEGATIVE:
        return -feature_delta
    if polarity == POLARITY_MIXED:
        return feature_delta
    raise ItemFeatureGeneratorError(f"unknown concept_feature_rule polarity: {polarity}")


def parse_concepts_from_semantic_json(
    semantic_json: dict[str, Any],
) -> tuple[ExtractedSemanticConcept, ...]:
    raw_concepts = semantic_json.get("concepts")
    if raw_concepts is None:
        raise ItemFeatureGeneratorError("item_semantic.semantic_json.concepts is required")
    if not isinstance(raw_concepts, list):
        raise ItemFeatureGeneratorError("item_semantic.semantic_json.concepts must be a list")

    concepts: list[ExtractedSemanticConcept] = []
    for index, entry in enumerate(raw_concepts):
        if not isinstance(entry, dict):
            raise ItemFeatureGeneratorError(
                f"item_semantic concept entry must be object (index={index})",
            )
        concept_code = entry.get("concept_code")
        if not isinstance(concept_code, str) or not concept_code.strip():
            raise ItemFeatureGeneratorError(
                f"item_semantic concept_code is required (index={index})",
            )
        confidence = entry.get("confidence")
        if not isinstance(confidence, (int, float)):
            raise ItemFeatureGeneratorError(
                f"item_semantic concept confidence must be numeric (index={index})",
            )
        source_type = entry.get("source_type")
        if not isinstance(source_type, str) or not source_type.strip():
            raise ItemFeatureGeneratorError(
                f"item_semantic concept source_type is required (index={index})",
            )
        concepts.append(
            ExtractedSemanticConcept(
                concept_code=concept_code,
                confidence=float(confidence),
                input_intent=str(entry.get("input_intent") or "neutral"),
                extraction_method=str(entry.get("extraction_method") or "rule"),
                source_type=source_type,
                assertion_polarity=str(entry.get("assertion_polarity") or "asserted"),
            ),
        )
    return tuple(concepts)


def build_rules_by_concept(
    rules: Iterable[ConceptFeatureRuleRecord],
) -> dict[str, tuple[ConceptFeatureRuleRecord, ...]]:
    grouped: dict[str, list[ConceptFeatureRuleRecord]] = {}
    for rule in rules:
        if not rule.is_active:
            continue
        grouped.setdefault(rule.concept_code, []).append(rule)
    return {concept_code: tuple(rows) for concept_code, rows in grouped.items()}


def aggregate_item_feature_deltas(
    concepts: tuple[ExtractedSemanticConcept, ...],
    *,
    rules_by_concept: dict[str, tuple[ConceptFeatureRuleRecord, ...]],
) -> tuple[dict[str, float], int]:
    """Concept 集合から 8 軸 delta を集約する（§8.3.1）。"""
    deltas = zero_feature_vector()
    rule_hit_count = 0

    for concept in concepts:
        concept_rules = rules_by_concept.get(concept.concept_code, ())
        if not concept_rules:
            continue

        source_weight = resolve_source_weight(concept.source_type)
        if source_weight == 0.0:
            continue

        for rule in concept_rules:
            if rule.feature_code not in deltas:
                continue
            signed_delta = apply_polarity(rule.feature_delta, rule.polarity)
            contribution = signed_delta * source_weight * concept.confidence
            deltas[rule.feature_code] += contribution
            rule_hit_count += 1

    return deltas, rule_hit_count


def count_raw_clip_applied(
    raw_values: dict[str, float],
    clipped_values: dict[str, float],
) -> int:
    return sum(
        1
        for axis in MVP_FEATURE_CODES
        if axis in raw_values
        and axis in clipped_values
        and not math.isclose(raw_values[axis], clipped_values[axis], abs_tol=1e-12)
    )


def assert_finite_feature_vector(vector: dict[str, float]) -> None:
    for axis, value in vector.items():
        if math.isnan(value) or math.isinf(value):
            raise ItemFeatureGeneratorError(
                f"non-finite raw feature value for axis {axis}",
            )
