"""Batch infrastructure scaffold (Phase4a)."""

from batch.infrastructure.db import DbWriteResult, DbWriter, ScaffoldDbWriter
from batch.infrastructure.external_ai import (
    ExternalAiClient,
    ExternalAiResponse,
    ScaffoldExternalAiClient,
)
from batch.infrastructure.logger import BatchLogger, LogContext, LogRecord, ScaffoldBatchLogger
from batch.infrastructure.object_storage import (
    ObjectRef,
    ObjectStorageClient,
    ScaffoldObjectStorageClient,
    StoredObject,
)
from batch.infrastructure.rakuten import (
    RakutenApiClient,
    RakutenGenre,
    RakutenItem,
    RakutenRankingEntry,
    ScaffoldRakutenApiClient,
)

__all__ = [
    "BatchLogger",
    "DbWriteResult",
    "DbWriter",
    "ExternalAiClient",
    "ExternalAiResponse",
    "LogContext",
    "LogRecord",
    "ObjectRef",
    "ObjectStorageClient",
    "RakutenApiClient",
    "RakutenGenre",
    "RakutenItem",
    "RakutenRankingEntry",
    "ScaffoldBatchLogger",
    "ScaffoldDbWriter",
    "ScaffoldExternalAiClient",
    "ScaffoldObjectStorageClient",
    "ScaffoldRakutenApiClient",
    "StoredObject",
]
