"""Ports for MOD-RECO-010."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EmbeddingGenerationResult:
    """External Embedding API response (IF-EXT-005 logical contract)."""

    vector: tuple[float, ...]
    model_version_id: str
    dimensions: int


class EmbeddingApiClientPort(Protocol):
    """Embedding API boundary. Concrete client lives in infrastructure."""

    def generate(
        self,
        text: str,
        model_version_id: str,
        metadata: dict[str, str],
    ) -> EmbeddingGenerationResult: ...


class RunValidationPort(Protocol):
    """Optional recommendation_run validation for embedding model version."""

    def get_embedding_model_version_id(
        self,
        recommendation_run_id: str,
    ) -> str | None: ...
