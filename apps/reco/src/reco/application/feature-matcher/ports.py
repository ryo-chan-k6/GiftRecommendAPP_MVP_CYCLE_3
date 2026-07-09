"""Ports for MOD-RECO-014 (IF-DB-RECO-005 Item Feature Repository boundary)."""

from __future__ import annotations

from typing import Protocol

from reco.application.user_feature_generator.models import FeatureNormalizationParameters


class ItemFeatureRepositoryPort(Protocol):
    """item_feature 参照（IF-DB-RECO-005）。"""

    def fetch_item_features(
        self,
        item_ids: tuple[str, ...],
        semantic_config_version_id: str,
    ) -> dict[str, dict[str, float]]:
        """候補 item_id 集合に対する正規化済み 8 軸 feature 値。"""
        ...


class FeatureNormalizationPort(Protocol):
    """feature_normalization_version から sigmoid パラメータを解決する。"""

    def get_parameters(
        self,
        feature_normalization_version_id: str,
    ) -> FeatureNormalizationParameters | None:
        ...
