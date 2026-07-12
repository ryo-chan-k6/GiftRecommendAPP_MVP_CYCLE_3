"""Reco infrastructure scaffold (Phase4a)."""

from reco.infrastructure.db import DatabaseHealth, DatabaseSession, ScaffoldDatabaseSession
from reco.infrastructure.external_ai import (
    ExternalAiClient,
    ExternalAiResponse,
    ScaffoldExternalAiClient,
)
from reco.infrastructure.logger import LogContext, LogRecord, RecoLogger, ScaffoldRecoLogger
from reco.infrastructure.vector_store import (
    ScaffoldVectorStoreClient,
    VectorSearchResult,
    VectorStoreClient,
)

__all__ = [
    "DatabaseHealth",
    "DatabaseSession",
    "ExternalAiClient",
    "ExternalAiResponse",
    "LogContext",
    "LogRecord",
    "RecoLogger",
    "ScaffoldDatabaseSession",
    "ScaffoldExternalAiClient",
    "ScaffoldRecoLogger",
    "ScaffoldVectorStoreClient",
    "VectorSearchResult",
    "VectorStoreClient",
]
