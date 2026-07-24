"""Batch infrastructure scaffold (Phase4a)."""

from batch.infrastructure.db import (
    DatabaseError,
    DbWriteResult,
    DbWriter,
    PostgresDbWriter,
    ScaffoldDbWriter,
    create_db_writer,
    mask_database_url,
    resolve_job_db_writer,
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
    HttpRakutenApiClient,
    RakutenApiClient,
    RakutenGenre,
    RakutenItem,
    RakutenRankingEntry,
    ScaffoldRakutenApiClient,
    create_rakuten_client,
    resolve_live_rakuten_flag,
)

__all__ = [
    "BatchLogger",
    "DatabaseError",
    "DbWriteResult",
    "DbWriter",
    "ExternalAiClient",
    "ExternalAiResponse",
    "HttpRakutenApiClient",
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
    "create_rakuten_client",
    "mask_database_url",
    "resolve_job_db_writer",
    "resolve_live_rakuten_flag",
]
