"""In-memory repositories for MOD-RECO-007 unit tests and scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field

from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID

from .constants import (
    DEFAULT_CENTER_FEATURE,
    DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
    DEFAULT_K_FEATURE,
    NORMALIZATION_METHOD_SIGMOID,
    SOURCE_TYPE_AGGREGATED,
)
from .models import (
    FeatureNormalizationParameters,
    NormalizationBinding,
    UserFeatureInsertRow,
)
from .ports import (
    NormalizationRuleRepositoryPort,
    RunValidationPort,
    UserFeatureRepositoryPort,
)


def build_default_normalization_binding() -> NormalizationBinding:
    return NormalizationBinding(
        feature_normalization_version_id=DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
        parameters=FeatureNormalizationParameters(
            center_feature=DEFAULT_CENTER_FEATURE,
            k_feature=DEFAULT_K_FEATURE,
            normalization_method=NORMALIZATION_METHOD_SIGMOID,
        ),
    )


@dataclass
class InMemoryNormalizationRuleRepository:
    semantic_config_version_id: str = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    binding: NormalizationBinding | None = field(
        default_factory=build_default_normalization_binding,
    )
    should_fail_on_lookup: bool = False

    def get_active_normalization_binding(
        self,
        semantic_config_version_id: str,
    ) -> NormalizationBinding | None:
        if self.should_fail_on_lookup:
            raise RuntimeError("normalization_rule lookup failed")
        if semantic_config_version_id != self.semantic_config_version_id:
            return None
        return self.binding


@dataclass
class InMemoryUserFeatureRepository:
    user_semantic_runs: set[str] = field(default_factory=set)
    inserted_rows: list[UserFeatureInsertRow] = field(default_factory=list)
    should_fail_on_insert: bool = False
    reject_duplicate_insert: bool = True

    def register_user_semantic(self, recommendation_run_id: str) -> None:
        self.user_semantic_runs.add(recommendation_run_id)

    def has_user_semantic(self, recommendation_run_id: str) -> bool:
        return recommendation_run_id in self.user_semantic_runs

    def insert_user_features(self, rows: tuple[UserFeatureInsertRow, ...]) -> None:
        if self.should_fail_on_insert:
            raise RuntimeError("user_feature insert failed")
        if self.reject_duplicate_insert and rows:
            run_id = rows[0].recommendation_run_id
            if any(row.recommendation_run_id == run_id for row in self.inserted_rows):
                raise RuntimeError("duplicate user_feature insert for run")
        self.inserted_rows.extend(rows)


@dataclass
class InMemoryRunValidation:
    run_versions: dict[str, str] = field(default_factory=dict)

    def register_run(self, run_id: str, semantic_config_version_id: str) -> None:
        self.run_versions[run_id] = semantic_config_version_id

    def get_semantic_config_version_id(self, recommendation_run_id: str) -> str | None:
        return self.run_versions.get(recommendation_run_id)


def build_default_in_memory_repositories() -> tuple[
    NormalizationRuleRepositoryPort,
    UserFeatureRepositoryPort,
    RunValidationPort,
]:
    return (
        InMemoryNormalizationRuleRepository(),
        InMemoryUserFeatureRepository(),
        InMemoryRunValidation(),
    )


def build_default_user_feature_repository() -> InMemoryUserFeatureRepository:
    return InMemoryUserFeatureRepository()
