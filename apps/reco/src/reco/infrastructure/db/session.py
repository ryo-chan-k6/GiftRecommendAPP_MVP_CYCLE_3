"""Database session boundary for reco infrastructure."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

DbParams = tuple[Any, ...] | list[Any]
DbRow = dict[str, Any]

_SENSITIVE_URL_PATTERN = re.compile(
    r"(postgres(?:ql)?://)([^:@/]+)(?::([^@/]*))?@",
    re.IGNORECASE,
)


class DatabaseError(RuntimeError):
    """Raised when a database session operation fails."""


@dataclass(frozen=True)
class DatabaseHealth:
    """Health probe result for a database session."""

    is_available: bool
    backend: str


class DatabaseSession(Protocol):
    """Database access boundary."""

    @property
    def backend(self) -> str: ...

    def health_check(self) -> DatabaseHealth: ...

    def query(self, sql: str, params: DbParams | None = None) -> list[DbRow]: ...

    def query_one(self, sql: str, params: DbParams | None = None) -> DbRow | None: ...

    def execute(self, sql: str, params: DbParams | None = None) -> int: ...


def mask_database_url(url: str) -> str:
    """Redact credentials from a database URL before logging."""

    if url.strip() == "":
        return ""

    def _replace(match: re.Match[str]) -> str:
        protocol = match.group(1)
        user = match.group(2)
        password = match.group(3)
        masked_user = "" if user == "" else "***REDACTED***"
        masked_password = "" if password is None else ":***REDACTED***"
        return f"{protocol}{masked_user}{masked_password}@"

    return _SENSITIVE_URL_PATTERN.sub(_replace, url)


@dataclass
class ScaffoldDatabaseSession:
    """Placeholder session without a real database connection."""

    backend: str = "scaffold"
    is_available: bool = True
    query_rows: list[DbRow] = field(default_factory=list)
    affected_rows: int = 0
    operations: list[tuple[str, str, DbParams]] = field(default_factory=list)

    def health_check(self) -> DatabaseHealth:
        return DatabaseHealth(is_available=self.is_available, backend=self.backend)

    def query(self, sql: str, params: DbParams | None = None) -> list[DbRow]:
        self._assert_available()
        bound = tuple(params or ())
        self.operations.append(("query", sql, bound))
        return list(self.query_rows)

    def query_one(self, sql: str, params: DbParams | None = None) -> DbRow | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: DbParams | None = None) -> int:
        self._assert_available()
        bound = tuple(params or ())
        self.operations.append(("execute", sql, bound))
        return self.affected_rows

    def _assert_available(self) -> None:
        if not self.is_available:
            raise DatabaseError("database session is unavailable")


@dataclass
class PostgresDatabaseSession:
    """PostgreSQL session backed by psycopg."""

    database_url: str
    backend: str = "postgres"

    def health_check(self) -> DatabaseHealth:
        try:
            self.query_one("SELECT 1 AS ok")
            return DatabaseHealth(is_available=True, backend=self.backend)
        except Exception:  # noqa: BLE001 — health probe only
            return DatabaseHealth(is_available=False, backend=self.backend)

    def query(self, sql: str, params: DbParams | None = None) -> list[DbRow]:
        import psycopg
        from psycopg.rows import dict_row

        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, params or ())
                    return list(cur.fetchall())
        except Exception as exc:  # noqa: BLE001 — surface as DatabaseError
            raise DatabaseError(str(exc)) from exc

    def query_one(self, sql: str, params: DbParams | None = None) -> DbRow | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: DbParams | None = None) -> int:
        import psycopg

        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params or ())
                    conn.commit()
                    return cur.rowcount
        except Exception as exc:  # noqa: BLE001 — surface as DatabaseError
            raise DatabaseError(str(exc)) from exc


def create_database_session(
    database_url: str | None,
    *,
    fallback: DatabaseSession | None = None,
) -> DatabaseSession:
    """Build a database session from ``DATABASE_URL`` when a real URL is provided."""

    if database_url and not database_url.startswith("scaffold://"):
        return PostgresDatabaseSession(database_url=database_url)
    return fallback or ScaffoldDatabaseSession()
