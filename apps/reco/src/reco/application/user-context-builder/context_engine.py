"""preferred / non_preferred context assembly for MOD-RECO-009."""

from __future__ import annotations

import re
import unicodedata

from reco.domain.recommendation.inputs import (
    NonPreferredCondition,
    OccasionCondition,
    PreferredCondition,
    RelationshipCondition,
)
from reco.domain.recommendation.request import RecommendationRequest
from reco.domain.semantic_extraction import ExtractedSemanticConcept

from .constants import (
    EMBEDDING_QUERY_TEXT_MAX_LENGTH,
    FREE_TEXT_TRUNCATE_LENGTH,
    SEMANTIC_QUERY_TOP_K,
)
from .models import NonPreferredContext, PreferredContext, UserContext


def normalize_query_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text.strip())
    return re.sub(r"\s+", " ", normalized)


def _resolve_label(label: str | None, code: str) -> str:
    if label is not None and label.strip():
        return normalize_query_text(label)
    return normalize_query_text(code)


def build_context_query(
    relationship: RelationshipCondition,
    occasion: OccasionCondition,
) -> str:
    relationship_label = _resolve_label(
        relationship.relationship_label,
        relationship.relationship_code,
    )
    occasion_label = _resolve_label(
        occasion.occasion_label,
        occasion.occasion_code,
    )
    return " ".join(part for part in (relationship_label, occasion_label) if part)


def build_preferred_query(
    preferred_condition: PreferredCondition | None,
) -> str | None:
    if preferred_condition is None:
        return None

    parts: list[str] = []
    if preferred_condition.preferred_text and preferred_condition.preferred_text.strip():
        parts.append(normalize_query_text(preferred_condition.preferred_text))

    keywords = [
        normalize_query_text(keyword)
        for keyword in preferred_condition.preferred_keywords
        if keyword.strip()
    ]
    if keywords:
        parts.append(" ".join(keywords))

    if not parts:
        return None
    return " ".join(parts)


def build_free_text_query(free_text: str | None) -> str | None:
    if free_text is None or not free_text.strip():
        return None
    normalized = normalize_query_text(free_text)
    if len(normalized) > FREE_TEXT_TRUNCATE_LENGTH:
        return normalized[:FREE_TEXT_TRUNCATE_LENGTH]
    return normalized


def build_semantic_query(
    concepts: tuple[ExtractedSemanticConcept, ...],
    *,
    top_k: int = SEMANTIC_QUERY_TOP_K,
) -> str | None:
    if not concepts:
        return None
    ranked = sorted(concepts, key=lambda concept: concept.confidence, reverse=True)
    codes = [
        concept.concept_code
        for concept in ranked[:top_k]
        if concept.concept_code.strip()
    ]
    if not codes:
        return None
    return " ".join(codes)


def build_embedding_query_text(
    *,
    relationship: RelationshipCondition,
    occasion: OccasionCondition,
    preferred_text: str | None,
    free_text: str | None,
    max_length: int = EMBEDDING_QUERY_TEXT_MAX_LENGTH,
) -> str:
    relationship_label = _resolve_label(
        relationship.relationship_label,
        relationship.relationship_code,
    )
    occasion_label = _resolve_label(
        occasion.occasion_label,
        occasion.occasion_code,
    )

    parts: list[str] = []
    if relationship_label or occasion_label:
        parts.append(f"{relationship_label}への{occasion_label}。")

    if preferred_text and preferred_text.strip():
        parts.append(normalize_query_text(preferred_text))

    if free_text and free_text.strip():
        summary = normalize_query_text(free_text)
        if len(summary) > FREE_TEXT_TRUNCATE_LENGTH:
            summary = summary[:FREE_TEXT_TRUNCATE_LENGTH]
        parts.append(summary)

    text = "".join(parts)
    if text and not text.endswith("。"):
        text += "。"

    if len(text) > max_length:
        if max_length <= 1:
            return "…"
        text = text[: max_length - 1] + "…"
    return text


def build_avoid_query_text(
    non_preferred_condition: NonPreferredCondition | None,
) -> str | None:
    if non_preferred_condition is None:
        return None

    parts: list[str] = []
    if (
        non_preferred_condition.non_preferred_text
        and non_preferred_condition.non_preferred_text.strip()
    ):
        parts.append(normalize_query_text(non_preferred_condition.non_preferred_text))

    keywords = [
        normalize_query_text(keyword)
        for keyword in non_preferred_condition.non_preferred_keywords
        if keyword.strip()
    ]
    if keywords:
        parts.append(" ".join(keywords))

    if not parts:
        return None
    return " ".join(parts)


def assemble_user_context(
    *,
    request: RecommendationRequest,
    concepts: tuple[ExtractedSemanticConcept, ...],
    lambda_ctx: float,
) -> UserContext:
    if request.relationship is None or request.occasion is None:
        raise ValueError("relationship and occasion are required")

    preferred_context = PreferredContext(
        context_query=build_context_query(request.relationship, request.occasion),
        preferred_query=build_preferred_query(request.preferred_condition),
        free_text_query=build_free_text_query(request.free_text),
        semantic_query=build_semantic_query(concepts),
        embedding_query_text=build_embedding_query_text(
            relationship=request.relationship,
            occasion=request.occasion,
            preferred_text=(
                request.preferred_condition.preferred_text
                if request.preferred_condition is not None
                else None
            ),
            free_text=request.free_text,
        ),
    )
    non_preferred_context = NonPreferredContext(
        avoid_query_text=build_avoid_query_text(request.non_preferred_condition),
    )
    return UserContext(
        preferred_context=preferred_context,
        non_preferred_context=non_preferred_context,
        lambda_ctx=lambda_ctx,
    )
