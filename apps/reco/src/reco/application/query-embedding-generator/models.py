"""Domain types for MOD-RECO-010."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PreferredEmbedding:
    """Embedding Value Object for Retrieval preferred query (MVP)."""

    vector: tuple[float, ...]
    model_version_id: str
    dimensions: int
    source_text_hash: str | None = None


@dataclass(frozen=True)
class QueryEmbedding:
    """Query Embedding domain object for downstream MOD-RECO-012+."""

    preferred_embedding: PreferredEmbedding
