"""Batch observability writers (phase_log / error_log / api_call_log) for E4."""

from batch.application.observability.api_call_log import (
    ALLOWED_CALL_STATUSES,
    ALLOWED_SOURCE_APIS,
    ApiCallLogWriter,
    PostgresApiCallLogWriter,
    ScaffoldApiCallLogWriter,
)
from batch.application.observability.error_log import (
    ErrorLogWriter,
    PostgresErrorLogWriter,
    ScaffoldErrorLogWriter,
)
from batch.application.observability.factory import (
    BatchObservabilityWriters,
    create_api_call_log_writer,
    create_batch_observability_writers,
    create_error_log_writer,
    create_phase_log_writer,
)
from batch.application.observability.mapping import (
    GENRE_SYNC_APP_PHASE_TO_DDL,
    map_app_phase_status,
    map_app_phase_to_ddl,
)
from batch.application.observability.phase_log import (
    ALLOWED_BATCH_PHASE_NAMES,
    PhaseLogWriter,
    PostgresPhaseLogWriter,
    ScaffoldPhaseLogWriter,
)

__all__ = [
    "ALLOWED_BATCH_PHASE_NAMES",
    "ALLOWED_CALL_STATUSES",
    "ALLOWED_SOURCE_APIS",
    "ApiCallLogWriter",
    "BatchObservabilityWriters",
    "ErrorLogWriter",
    "GENRE_SYNC_APP_PHASE_TO_DDL",
    "PhaseLogWriter",
    "PostgresApiCallLogWriter",
    "PostgresErrorLogWriter",
    "PostgresPhaseLogWriter",
    "ScaffoldApiCallLogWriter",
    "ScaffoldErrorLogWriter",
    "ScaffoldPhaseLogWriter",
    "create_api_call_log_writer",
    "create_batch_observability_writers",
    "create_error_log_writer",
    "create_phase_log_writer",
    "map_app_phase_status",
    "map_app_phase_to_ddl",
]
