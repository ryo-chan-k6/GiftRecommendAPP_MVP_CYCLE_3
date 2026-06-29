"""Repository ports for MOD-RECO-009."""

from __future__ import annotations

from typing import Protocol

from .models import UserFeatureRow, UserMeaningInsertRow


class LambdaContextRuleRepositoryPort(Protocol):
    """Read-only lambda_ctx rule lookup."""

    def get_lambda_ctx(
        self,
        semantic_config_version_id: str,
        relationship_code: str,
        occasion_code: str,
    ) -> float | None: ...


class UserMeaningRepositoryPort(Protocol):
    """user_meaning INSERT (IF-DB-RECO-003)."""

    def insert_user_meaning(self, row: UserMeaningInsertRow) -> str: ...


class UserFeatureReadPort(Protocol):
    """Read-only user_feature rows for consistency validation."""

    def get_user_features_for_run(
        self,
        recommendation_run_id: str,
    ) -> tuple[UserFeatureRow, ...]: ...


class RunValidationPort(Protocol):
    """Read-only recommendation_run validation."""

    def get_semantic_config_version_id(self, recommendation_run_id: str) -> str | None: ...
