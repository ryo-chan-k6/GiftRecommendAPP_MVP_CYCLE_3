"""Database infrastructure scaffold."""

from reco.infrastructure.db.session import (
    DEFAULT_POOL_MAX_SIZE,
    DEFAULT_POOL_MIN_SIZE,
    DatabaseError,
    DatabaseHealth,
    DatabaseSession,
    PostgresDatabaseSession,
    ScaffoldDatabaseSession,
    create_database_session,
    mask_database_url,
)

__all__ = [
    "DEFAULT_POOL_MAX_SIZE",
    "DEFAULT_POOL_MIN_SIZE",
    "DatabaseError",
    "DatabaseHealth",
    "DatabaseSession",
    "PostgresDatabaseSession",
    "ScaffoldDatabaseSession",
    "create_database_session",
    "mask_database_url",
]
