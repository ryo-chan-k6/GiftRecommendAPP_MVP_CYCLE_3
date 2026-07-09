"""Vector validation helpers for MOD-RECO-010."""

from __future__ import annotations

import math

from .constants import EMBEDDING_DIMENSIONS
from .errors import QueryEmbeddingGenerationError


def validate_embedding_vector(vector: tuple[float, ...] | list[float]) -> tuple[float, ...]:
    """Ensure vector length and numeric sanity per module spec §8.3.1."""
    if len(vector) != EMBEDDING_DIMENSIONS:
        raise QueryEmbeddingGenerationError(
            f"embedding vector dimension mismatch: expected {EMBEDDING_DIMENSIONS}, "
            f"got {len(vector)}",
        )

    normalized: list[float] = []
    for value in vector:
        if math.isnan(value) or math.isinf(value):
            raise QueryEmbeddingGenerationError("embedding vector contains non-finite value")
        normalized.append(float(value))

    return tuple(normalized)
