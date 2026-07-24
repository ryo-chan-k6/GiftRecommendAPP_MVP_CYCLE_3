"""External AI infrastructure (Embedding / LLM scaffold + HTTP)."""

from batch.infrastructure.external_ai.client import (
    EmbeddingApiError,
    EmbeddingClient,
    EmbeddingResponse,
    ExternalAiClient,
    ExternalAiResponse,
    HttpEmbeddingClient,
    ScaffoldEmbeddingClient,
    ScaffoldExternalAiClient,
    create_embedding_client,
    mask_openai_secret,
    resolve_live_embedding_flag,
)

__all__ = [
    "EmbeddingApiError",
    "EmbeddingClient",
    "EmbeddingResponse",
    "ExternalAiClient",
    "ExternalAiResponse",
    "HttpEmbeddingClient",
    "ScaffoldEmbeddingClient",
    "ScaffoldExternalAiClient",
    "create_embedding_client",
    "mask_openai_secret",
    "resolve_live_embedding_flag",
]
