"""Scaffold wiring helpers for MOD-RECO-010."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .generator import QueryEmbeddingGenerator, build_default_query_embedding_generator
from .in_memory_client import (
    InMemoryEmbeddingApiClient,
    build_default_in_memory_embedding_client,
)
from .in_memory_repository import (
    InMemoryRunValidation,
    build_default_in_memory_run_validation,
)


def build_scaffold_query_embedding_generator() -> QueryEmbeddingGenerator:
    """Build Query Embedding Generator backed by in-memory client (MVP scaffold)."""
    return QueryEmbeddingGenerator(
        embedding_client=build_default_in_memory_embedding_client(),
        run_validation=build_default_in_memory_run_validation(),
        logger=ScaffoldRecoLogger(),
    )


__all__ = [
    "InMemoryEmbeddingApiClient",
    "InMemoryRunValidation",
    "QueryEmbeddingGenerator",
    "build_default_in_memory_embedding_client",
    "build_default_in_memory_run_validation",
    "build_default_query_embedding_generator",
    "build_scaffold_query_embedding_generator",
]
