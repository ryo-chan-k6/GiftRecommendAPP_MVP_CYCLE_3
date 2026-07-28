"""Factory for Batch observability writers (same switch as ``create_job_run_tracker``)."""

from __future__ import annotations

from dataclasses import dataclass

from batch.application.observability.api_call_log import (
    ApiCallLogWriter,
    PostgresApiCallLogWriter,
    ScaffoldApiCallLogWriter,
)
from batch.application.observability.error_log import (
    ErrorLogWriter,
    PostgresErrorLogWriter,
    ScaffoldErrorLogWriter,
)
from batch.application.observability.phase_log import (
    PhaseLogWriter,
    PostgresPhaseLogWriter,
    ScaffoldPhaseLogWriter,
)
from batch.infrastructure.db import DbWriter, create_db_writer


def _use_scaffold(*, scaffold_demo: bool, database_url: str | None) -> bool:
    if scaffold_demo:
        return True
    if not database_url or database_url.startswith("scaffold://"):
        return True
    return False


def create_phase_log_writer(
    *,
    scaffold_demo: bool,
    database_url: str | None,
    db_writer: DbWriter | None = None,
) -> PhaseLogWriter:
    """Resolve PhaseLogWriter for CLI jobs (same switch policy as ``create_job_run_tracker``).

    - ``scaffold_demo`` / unset・empty / ``scaffold://...`` → ``ScaffoldPhaseLogWriter``
    - otherwise → ``PostgresPhaseLogWriter``（``db_writer`` 無ければ ``create_db_writer``）
    """

    if _use_scaffold(scaffold_demo=scaffold_demo, database_url=database_url):
        return ScaffoldPhaseLogWriter()
    writer = db_writer if db_writer is not None else create_db_writer(database_url)
    return PostgresPhaseLogWriter(db_writer=writer)


def create_error_log_writer(
    *,
    scaffold_demo: bool,
    database_url: str | None,
    db_writer: DbWriter | None = None,
) -> ErrorLogWriter:
    """Resolve ErrorLogWriter for CLI jobs (same switch policy as ``create_job_run_tracker``)."""

    if _use_scaffold(scaffold_demo=scaffold_demo, database_url=database_url):
        return ScaffoldErrorLogWriter()
    writer = db_writer if db_writer is not None else create_db_writer(database_url)
    return PostgresErrorLogWriter(db_writer=writer)


def create_api_call_log_writer(
    *,
    scaffold_demo: bool,
    database_url: str | None,
    db_writer: DbWriter | None = None,
) -> ApiCallLogWriter:
    """Resolve ApiCallLogWriter for CLI jobs (same switch policy as ``create_job_run_tracker``)."""

    if _use_scaffold(scaffold_demo=scaffold_demo, database_url=database_url):
        return ScaffoldApiCallLogWriter()
    writer = db_writer if db_writer is not None else create_db_writer(database_url)
    return PostgresApiCallLogWriter(db_writer=writer)


@dataclass(frozen=True)
class BatchObservabilityWriters:
    """Paired phase / error / api_call writers resolved with the same scaffold / Postgres policy."""

    phase_log_writer: PhaseLogWriter
    error_log_writer: ErrorLogWriter
    api_call_log_writer: ApiCallLogWriter


def create_batch_observability_writers(
    *,
    scaffold_demo: bool,
    database_url: str | None,
    db_writer: DbWriter | None = None,
) -> BatchObservabilityWriters:
    """Create phase / error / api_call writers with a shared DbWriter when targeting Postgres."""

    if _use_scaffold(scaffold_demo=scaffold_demo, database_url=database_url):
        return BatchObservabilityWriters(
            phase_log_writer=ScaffoldPhaseLogWriter(),
            error_log_writer=ScaffoldErrorLogWriter(),
            api_call_log_writer=ScaffoldApiCallLogWriter(),
        )
    writer = db_writer if db_writer is not None else create_db_writer(database_url)
    return BatchObservabilityWriters(
        phase_log_writer=PostgresPhaseLogWriter(db_writer=writer),
        error_log_writer=PostgresErrorLogWriter(db_writer=writer),
        api_call_log_writer=PostgresApiCallLogWriter(db_writer=writer),
    )
