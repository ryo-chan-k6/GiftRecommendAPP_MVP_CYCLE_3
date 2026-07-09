"""In-memory repositories for MOD-RECO-014 unit tests and scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field

from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
from reco.application.user_feature_generator.constants import (
    DEFAULT_CENTER_FEATURE,
    DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
    DEFAULT_K_FEATURE,
    NORMALIZATION_METHOD_SIGMOID,
)
from reco.application.user_feature_generator.models import FeatureNormalizationParameters
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES

from .ports import FeatureNormalizationPort, ItemFeatureRepositoryPort


def build_default_normalization_parameters() -> FeatureNormalizationParameters:
    return FeatureNormalizationParameters(
        center_feature=DEFAULT_CENTER_FEATURE,
        k_feature=DEFAULT_K_FEATURE,
        normalization_method=NORMALIZATION_METHOD_SIGMOID,
    )


@dataclass
class InMemoryFeatureNormalizationRepository:
    """feature_normalization_version_id → sigmoid パラメータ（MVP scaffold）。"""

    bindings: dict[str, FeatureNormalizationParameters] = field(
        default_factory=lambda: {
            DEFAULT_FEATURE_NORMALIZATION_VERSION_ID: build_default_normalization_parameters(),
        },
    )
    should_fail_on_lookup: bool = False

    def get_parameters(
        self,
        feature_normalization_version_id: str,
    ) -> FeatureNormalizationParameters | None:
        if self.should_fail_on_lookup:
            raise RuntimeError("normalization parameter lookup failed")
        return self.bindings.get(feature_normalization_version_id)


@dataclass(frozen=True)
class InMemoryItemFeatureRecord:
    """item_feature 行集合（item × semantic version）。"""

    item_id: str
    semantic_config_version_id: str
    features: dict[str, float]


@dataclass
class InMemoryItemFeatureRepository:
    """item_feature 参照の in-memory 実装。"""

    records: dict[str, InMemoryItemFeatureRecord] = field(default_factory=dict)
    should_fail_on_fetch: bool = False

    def register_item_feature(self, record: InMemoryItemFeatureRecord) -> None:
        self.records[record.item_id] = record

    def fetch_item_features(
        self,
        item_ids: tuple[str, ...],
        semantic_config_version_id: str,
    ) -> dict[str, dict[str, float]]:
        if self.should_fail_on_fetch:
            raise RuntimeError("item_feature fetch failed")

        result: dict[str, dict[str, float]] = {}
        for item_id in item_ids:
            record = self.records.get(item_id)
            if record is None:
                continue
            if record.semantic_config_version_id != semantic_config_version_id:
                continue
            result[item_id] = dict(record.features)
        return result


def build_uniform_item_features(value: float = 0.5) -> dict[str, float]:
    return {axis: value for axis in MVP_FEATURE_CODES}


def build_default_in_memory_item_feature_repository() -> InMemoryItemFeatureRepository:
    repo = InMemoryItemFeatureRepository()
    for item_id, formality in (
        ("item-001", 0.65),
        ("item-002", 0.40),
    ):
        repo.register_item_feature(
            InMemoryItemFeatureRecord(
                item_id=item_id,
                semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
                features={
                    "formality": formality,
                    "safety": 0.7,
                    "brand_appropriateness": 0.6,
                    "emotion": 0.55,
                    "novelty": 0.5,
                    "intimacy": 0.45,
                    "symbolic_identity": 0.5,
                    "story_richness": 0.4,
                },
            ),
        )
    return repo


def build_default_in_memory_repositories() -> tuple[
    InMemoryItemFeatureRepository,
    InMemoryFeatureNormalizationRepository,
]:
    return (
        build_default_in_memory_item_feature_repository(),
        InMemoryFeatureNormalizationRepository(),
    )


__all__ = [
    "InMemoryFeatureNormalizationRepository",
    "InMemoryItemFeatureRecord",
    "InMemoryItemFeatureRepository",
    "build_default_in_memory_item_feature_repository",
    "build_default_in_memory_repositories",
    "build_default_normalization_parameters",
    "build_uniform_item_features",
]
