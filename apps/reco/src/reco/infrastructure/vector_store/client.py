"""Vector store client scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class VectorSearchResult:
    """Single vector search hit."""

    item_id: str
    score: float


class VectorStoreClient(Protocol):
    """Vector similarity search boundary (Phase4a protocol)."""

    def search(
        self,
        query_embedding: tuple[float, ...],
        *,
        top_k: int,
    ) -> tuple[VectorSearchResult, ...]: ...


@dataclass
class ScaffoldVectorStoreClient:
    """Phase4a placeholder client without pgvector or external index."""

    results: tuple[VectorSearchResult, ...] = ()
    search_calls: list[dict[str, object]] = field(default_factory=list)

    def search(
        self,
        query_embedding: tuple[float, ...],
        *,
        top_k: int,
    ) -> tuple[VectorSearchResult, ...]:
        self.search_calls.append(
            {
                "query_embedding": query_embedding,
                "top_k": top_k,
            }
        )
        return self.results[:top_k]
