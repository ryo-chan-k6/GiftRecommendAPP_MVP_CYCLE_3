"""In-memory run validation for MOD-RECO-010 scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field

from reco.application.config_version_resolver import DEFAULT_EMBEDDING_MODEL_VERSION_ID

from .ports import RunValidationPort


@dataclass
class InMemoryRunValidation:
    """Read-only recommendation_run embedding model version lookup."""

    runs_by_id: dict[str, str] = field(default_factory=dict)

    def register_run(
        self,
        recommendation_run_id: str,
        embedding_model_version_id: str = DEFAULT_EMBEDDING_MODEL_VERSION_ID,
    ) -> None:
        self.runs_by_id[recommendation_run_id] = embedding_model_version_id

    def get_embedding_model_version_id(
        self,
        recommendation_run_id: str,
    ) -> str | None:
        return self.runs_by_id.get(recommendation_run_id)


def build_default_in_memory_run_validation() -> InMemoryRunValidation:
    return InMemoryRunValidation()
