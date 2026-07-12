"""Domain types for MOD-RECO-006."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConceptFeatureRuleRecord:
    """Single concept_feature_rule row (sparse seed compatible)."""

    concept_code: str
    feature_code: str
    feature_delta: float
    polarity: str


@dataclass(frozen=True)
class InternalFeatureIntegrationWeights:
    """Internal condition integration weights from feature_integration_rule."""

    preferred_weight: float
    avoid_weight: float
    free_text_weight: float


@dataclass(frozen=True)
class InternalFeatureEstimate:
    """Internal condition feature delta estimation result (Run-scoped memory only)."""

    preferred_delta: dict[str, float]
    avoid_delta: dict[str, float]
    free_text_delta: dict[str, float]
    internal_feature_delta: dict[str, float]
    applied_concept_count: int
    semantic_config_version_id: str
    estimation_method: str
