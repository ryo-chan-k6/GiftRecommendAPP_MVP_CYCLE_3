"""Domain types for MOD-RECO-007."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FeatureNormalizationParameters:
    """Sigmoid parameters from feature_normalization_version.parameter_json."""

    center_feature: float
    k_feature: float
    normalization_method: str


@dataclass(frozen=True)
class NormalizationBinding:
    """Active normalization_rule binding for a semantic_config_version."""

    feature_normalization_version_id: str
    parameters: FeatureNormalizationParameters


@dataclass(frozen=True)
class UserFeatureInsertRow:
    """Single user_feature table INSERT row (IF-DB-RECO-003)."""

    recommendation_run_id: str
    feature_code: str
    feature_value: float
    feature_normalization_version_id: str
    source_type: str
    generated_at: datetime


@dataclass(frozen=True)
class UserFeature:
    """Normalized User Feature domain object (Run-scoped memory + DB mirror)."""

    recommendation_run_id: str
    features: dict[str, float]
    user_feature_raw: dict[str, float]
    feature_normalization_version_id: str
    semantic_config_version_id: str
    generated_at: datetime
