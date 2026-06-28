"""Repository ports for MOD-RECO-007."""

from __future__ import annotations

from typing import Protocol

from .models import NormalizationBinding, UserFeatureInsertRow


class NormalizationRuleRepositoryPort(Protocol):
    """Read-only normalization_rule / feature_normalization_version access."""

    def get_active_normalization_binding(
        self,
        semantic_config_version_id: str,
    ) -> NormalizationBinding | None: ...


class UserFeatureRepositoryPort(Protocol):
    """user_feature INSERT and user_semantic precondition checks."""

    def has_user_semantic(self, recommendation_run_id: str) -> bool: ...

    def insert_user_features(self, rows: tuple[UserFeatureInsertRow, ...]) -> None: ...


class RunValidationPort(Protocol):
    """Read-only recommendation_run validation for User Feature generation."""

    def get_semantic_config_version_id(self, recommendation_run_id: str) -> str | None: ...
