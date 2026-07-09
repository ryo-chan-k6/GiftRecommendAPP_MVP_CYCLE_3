"""In-memory repositories for MOD-RECO-008 unit tests and scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field

from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID

from .models import MeaningProjectionWeights, UserFeatureRow
from .ports import (
    MeaningProjectionConfigRepositoryPort,
    RunValidationPort,
    UserFeatureReadPort,
)


def build_default_projection_weights() -> MeaningProjectionWeights:
    """Default MVP weights: all unset → simple average per group."""
    return MeaningProjectionWeights()


@dataclass
class InMemoryMeaningProjectionConfigRepository:
    semantic_config_version_id: str = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    weights: MeaningProjectionWeights | None = field(
        default_factory=build_default_projection_weights,
    )
    should_fail_on_lookup: bool = False

    def get_weights(
        self,
        semantic_config_version_id: str,
    ) -> MeaningProjectionWeights | None:
        if self.should_fail_on_lookup:
            raise RuntimeError("projection weight lookup failed")
        if semantic_config_version_id != self.semantic_config_version_id:
            return None
        return self.weights


@dataclass
class InMemoryUserFeatureReadRepository:
    rows_by_run: dict[str, tuple[UserFeatureRow, ...]] = field(default_factory=dict)

    def register_user_features(
        self,
        recommendation_run_id: str,
        rows: tuple[UserFeatureRow, ...],
    ) -> None:
        self.rows_by_run[recommendation_run_id] = rows

    def get_user_features_for_run(
        self,
        recommendation_run_id: str,
    ) -> tuple[UserFeatureRow, ...]:
        return self.rows_by_run.get(recommendation_run_id, ())


@dataclass
class InMemoryRunValidation:
    run_versions: dict[str, str] = field(default_factory=dict)

    def register_run(self, run_id: str, semantic_config_version_id: str) -> None:
        self.run_versions[run_id] = semantic_config_version_id

    def get_semantic_config_version_id(self, recommendation_run_id: str) -> str | None:
        return self.run_versions.get(recommendation_run_id)


def build_default_in_memory_repositories() -> tuple[
    MeaningProjectionConfigRepositoryPort,
    UserFeatureReadPort,
    RunValidationPort,
]:
    return (
        InMemoryMeaningProjectionConfigRepository(),
        InMemoryUserFeatureReadRepository(),
        InMemoryRunValidation(),
    )
