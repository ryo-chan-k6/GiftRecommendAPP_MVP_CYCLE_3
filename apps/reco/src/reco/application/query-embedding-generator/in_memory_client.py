"""In-memory Embedding API client for unit tests and scaffold."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from reco.application.config_version_resolver import DEFAULT_EMBEDDING_MODEL_VERSION_ID

from .constants import EMBEDDING_DIMENSIONS
from .ports import EmbeddingGenerationResult


def _deterministic_vector(text: str, *, dimensions: int = EMBEDDING_DIMENSIONS) -> tuple[float, ...]:
    """Build a stable pseudo-embedding without outbound API calls."""
    digest = hashlib.sha256(text.encode()).digest()
    values: list[float] = []
    index = 0
    while len(values) < dimensions:
        chunk = digest[index % len(digest)]
        values.append((chunk / 255.0) * 2.0 - 1.0)
        index += 1
    return tuple(values)


@dataclass
class InMemoryEmbeddingApiClient:
    """Scaffold Embedding API client (no secret, no outbound HTTP)."""

    default_model_version_id: str = DEFAULT_EMBEDDING_MODEL_VERSION_ID
    generate_calls: list[dict[str, object]] = field(default_factory=list)

    def generate(
        self,
        text: str,
        model_version_id: str,
        metadata: dict[str, str],
    ) -> EmbeddingGenerationResult:
        self.generate_calls.append(
            {
                "text": text,
                "model_version_id": model_version_id,
                "metadata": dict(metadata),
            },
        )
        return EmbeddingGenerationResult(
            vector=_deterministic_vector(text),
            model_version_id=model_version_id,
            dimensions=EMBEDDING_DIMENSIONS,
        )


def build_default_in_memory_embedding_client() -> InMemoryEmbeddingApiClient:
    return InMemoryEmbeddingApiClient()
