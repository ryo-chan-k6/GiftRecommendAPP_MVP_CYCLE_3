"""Batch infrastructure scaffold (Phase4a)."""

from batch.infrastructure.db import (
    DatabaseError,
    DbWriteResult,
    DbWriter,
    PostgresDbWriter,
    ScaffoldDbWriter,
    create_db_writer,
    mask_database_url,
)
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
    "DatabaseError",
    "DbWriteResult",
    "DbWriter",
    "ExternalAiClient",
    "ExternalAiResponse",
    "LogContext",
    "LogRecord",
    "ObjectRef",
    "ObjectStorageClient",
    "PostgresDbWriter",
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
    "create_db_writer",
    "mask_database_url",
]
