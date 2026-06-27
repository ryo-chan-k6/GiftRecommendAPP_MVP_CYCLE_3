"""Domain types for MOD-RECO-005."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

FeatureVector = Mapping[str, float]


@dataclass(frozen=True)
class ExternalFeatureEstimate:
    """External condition feature raw estimation result (Run-scoped memory only)."""

    relationship_code: str
    occasion_code: str
    relationship_feature: dict[str, float]
    occasion_feature: dict[str, float]
    pair_delta: dict[str, float]
    external_feature_raw: dict[str, float]
    semantic_config_version_id: str
    estimation_method: str


@dataclass(frozen=True)
class FeatureIntegrationWeights:
    relationship_weight: float
    occasion_weight: float
