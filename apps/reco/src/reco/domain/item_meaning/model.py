"""Item Meaning placeholder model."""

from __future__ import annotations

from dataclasses import dataclass

from reco.domain.gift_meaning.features import FeatureVector


@dataclass(frozen=True)
class ItemMeaning:
    """Item Meaning aggregate root placeholder (Phase4a)."""

    item_id: str
    normalized_features: FeatureVector | None = None
    is_recommendable: bool = True
