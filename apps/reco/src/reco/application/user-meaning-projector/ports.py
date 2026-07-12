"""Repository ports for MOD-RECO-008."""

from __future__ import annotations

from typing import Protocol

from .models import MeaningProjectionWeights, UserFeatureRow


class MeaningProjectionConfigRepositoryPort(Protocol):
    """Read-only semantic_config_version projection weight access."""

    def get_weights(
        self,
        semantic_config_version_id: str,
    ) -> MeaningProjectionWeights | None: ...


class UserFeatureReadPort(Protocol):
    """Read-only user_feature rows for consistency validation."""

    def get_user_features_for_run(
        self,
        recommendation_run_id: str,
    ) -> tuple[UserFeatureRow, ...]: ...


class RunValidationPort(Protocol):
    """Read-only recommendation_run validation for User Meaning projection."""

    def get_semantic_config_version_id(self, recommendation_run_id: str) -> str | None: ...
