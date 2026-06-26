"""Recommendation Request input value objects (Phase4a type scaffold).

正本: RecommendationRequest定義書 / OpenAPI NormalizedRecommendationRequest
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True)
class RelationshipCondition:
    """Gift context: who the gift is for."""

    relationship_code: str
    relationship_label: str | None = None


@dataclass(frozen=True)
class OccasionCondition:
    """Gift context: why the gift is given."""

    occasion_code: str
    occasion_label: str | None = None


@dataclass(frozen=True)
class BudgetCondition:
    """Hard filter budget range."""

    budget_min: int | None = None
    budget_max: int | None = None
    currency: str | None = None
    tax_included: bool | None = None


@dataclass(frozen=True)
class PreferredCondition:
    """Relative preference toward desired gift characteristics."""

    preferred_text: str | None = None
    preferred_keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class NonPreferredCondition:
    """Relative preference to avoid certain characteristics."""

    non_preferred_text: str | None = None
    non_preferred_keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class NgCondition:
    """Absolute exclusion conditions."""

    ng_text: str | None = None
    ng_keywords: tuple[str, ...] = ()
    ng_categories: tuple[str, ...] = ()


class ExecutionMode(StrEnum):
    """Recommendation execution mode."""

    UI = "ui"
    EVALUATION = "evaluation"
    BATCH = "batch"


@dataclass(frozen=True)
class ExecutionCondition:
    """Execution controls for ranking and observability."""

    mode: ExecutionMode
    top_k: int | None = None
    candidate_limit: int | None = None
    include_reason: bool | None = None
    include_debug_info: bool | None = None
    eval_case_id: str | None = None
    semantic_config_version_id: str | None = None
    config_name: str | None = None
    version_label: str | None = None
    model_version_id: str | None = None
