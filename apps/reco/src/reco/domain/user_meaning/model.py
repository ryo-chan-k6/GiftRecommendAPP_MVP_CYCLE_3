"""User Meaning placeholder model."""

from __future__ import annotations

from dataclasses import dataclass

from reco.domain.gift_meaning.features import FeatureVector


@dataclass(frozen=True)
class UserMeaning:
    """User Meaning aggregate root placeholder (Phase4a)."""

    run_id: str
    normalized_features: FeatureVector | None = None
    lambda_ctx: float | None = None
