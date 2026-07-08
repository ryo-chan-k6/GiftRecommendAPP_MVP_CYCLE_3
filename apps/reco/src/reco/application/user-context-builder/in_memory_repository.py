"""In-memory repositories for MOD-RECO-009 unit tests and scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID

from .errors import UserContextBuildError
from .models import UserFeatureRow, UserMeaningInsertRow
from .ports import (
    LambdaContextRuleRepositoryPort,
    RunValidationPort,
    UserFeatureReadPort,
    UserMeaningRepositoryPort,
)


@dataclass
class InMemoryLambdaContextRuleRepository:
    """MVP scaffold: returns null by default → 0.5 fallback path."""

    rules: dict[tuple[str, str, str], float] = field(default_factory=dict)

    def register_rule(
        self,
        semantic_config_version_id: str,
        relationship_code: str,
        occasion_code: str,
        lambda_ctx: float,
    ) -> None:
        self.rules[(semantic_config_version_id, relationship_code, occasion_code)] = (
            lambda_ctx
        )

    def get_lambda_ctx(
        self,
        semantic_config_version_id: str,
        relationship_code: str,
        occasion_code: str,
    ) -> float | None:
        return self.rules.get(
            (semantic_config_version_id, relationship_code, occasion_code),
        )


@dataclass
class InMemoryUserMeaningRepository:
    rows_by_run: dict[str, UserMeaningInsertRow] = field(default_factory=dict)
    ids_by_run: dict[str, str] = field(default_factory=dict)

    def insert_user_meaning(self, row: UserMeaningInsertRow) -> str:
        if row.recommendation_run_id in self.rows_by_run:
            raise UserContextBuildError(
                f"user_meaning already exists for run: {row.recommendation_run_id}",
            )
        user_meaning_id = str(uuid4())
        self.rows_by_run[row.recommendation_run_id] = row
        self.ids_by_run[row.recommendation_run_id] = user_meaning_id
        return user_meaning_id


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
    LambdaContextRuleRepositoryPort,
    UserMeaningRepositoryPort,
    UserFeatureReadPort,
    RunValidationPort,
]:
    return (
        InMemoryLambdaContextRuleRepository(),
        InMemoryUserMeaningRepository(),
        InMemoryUserFeatureReadRepository(),
        InMemoryRunValidation(),
    )


DEFAULT_SEMANTIC_CONFIG_VERSION = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
