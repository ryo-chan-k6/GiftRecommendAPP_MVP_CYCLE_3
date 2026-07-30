"""Database session boundary for reco infrastructure."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger("reco.infrastructure.db.session")

DbParams = tuple[Any, ...] | list[Any]
DbRow = dict[str, Any]

_SENSITIVE_URL_PATTERN = re.compile(
    r"(postgres(?:ql)?://)([^:@/]+)(?::([^@/]*))?@",
    re.IGNORECASE,
)

# Fly stg: 512MB / shared CPU 1。推薦は同期直列想定（#1737 Human 決定）。
DEFAULT_POOL_MIN_SIZE = 1
DEFAULT_POOL_MAX_SIZE = 2
# 接続取得待ち。PIPELINE_HARD_TIMEOUT_MS（4,000ms）内に収めるため既定より短くする。
DEFAULT_POOL_TIMEOUT_SECONDS = 2.0
# 起動時ウォームアップの上限。DB 到達不能時に lifespan を止めないため有限にする。
DEFAULT_POOL_OPEN_TIMEOUT_SECONDS = 5.0


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

    def open(self) -> None:
        """No-op for Protocol-compatible lifecycle hooks."""

    def close(self) -> None:
        """No-op for Protocol-compatible lifecycle hooks."""

    def _assert_available(self) -> None:
        if not self.is_available:
            raise DatabaseError("database session is unavailable")


class PostgresDatabaseSession:
    """PostgreSQL session backed by ``psycopg_pool.ConnectionPool``.

    The pool is owned by this session unless an external ``pool`` is injected
    (unit tests). Construction does not open connections; call ``open()`` (or
    let the first query open lazily) so unit tests can construct without a live DB.
    """

    backend: str = "postgres"

    def __init__(
        self,
        *,
        database_url: str,
        pool: Any | None = None,
        min_size: int = DEFAULT_POOL_MIN_SIZE,
        max_size: int = DEFAULT_POOL_MAX_SIZE,
        timeout: float = DEFAULT_POOL_TIMEOUT_SECONDS,
        open_timeout: float = DEFAULT_POOL_OPEN_TIMEOUT_SECONDS,
    ) -> None:
        if database_url.strip() == "":
            raise DatabaseError("DATABASE_URL is empty")
        if min_size < 0 or max_size < 1 or min_size > max_size:
            raise DatabaseError(
                f"invalid pool size: min_size={min_size}, max_size={max_size}"
            )
        if timeout <= 0 or open_timeout <= 0:
            raise DatabaseError(
                f"invalid pool timeout: timeout={timeout}, open_timeout={open_timeout}"
            )

        self.database_url = database_url
        self.min_size = min_size
        self.max_size = max_size
        self.timeout = timeout
        self.open_timeout = open_timeout
        self._owns_pool = pool is None
        self._opened = pool is not None
        if pool is not None:
            self._pool = pool
        else:
            from psycopg_pool import ConnectionPool

            # open=False: コンストラクタ時点では接続しない（unit test / lifespan 分離）
            self._pool = ConnectionPool(
                conninfo=database_url,
                min_size=min_size,
                max_size=max_size,
                timeout=timeout,
                open=False,
                name="reco-postgres",
            )

    def open(self) -> None:
        """Open the pool and warm ``min_size`` connections when this session owns it."""

        if self._opened:
            return
        # ウォームアップ失敗でも起動は継続する（pool が background で再接続を続け、
        # 到達不能なら各 query が DatabaseError として失敗する）。
        try:
            self._pool.open(wait=True, timeout=self.open_timeout)
        except Exception as exc:  # noqa: BLE001 — startup best-effort
            logger.warning(
                "database pool warmup failed: url=%s open_timeout=%s error=%s",
                mask_database_url(self.database_url),
                self.open_timeout,
                exc,
            )
        self._opened = True

    def close(self) -> None:
        """Close the pool when this session owns it."""

        if not self._owns_pool:
            return
        if not self._opened:
            # ConnectionPool.close() is safe even if never opened, but avoid noise.
            try:
                self._pool.close()
            except Exception:  # noqa: BLE001 — shutdown best-effort
                pass
            return
        try:
            self._pool.close()
        except Exception:  # noqa: BLE001 — shutdown best-effort
            pass
        finally:
            self._opened = False

    def health_check(self) -> DatabaseHealth:
        try:
            self.query_one("SELECT 1 AS ok")
            return DatabaseHealth(is_available=True, backend=self.backend)
        except Exception:  # noqa: BLE001 — health probe only
            return DatabaseHealth(is_available=False, backend=self.backend)

    def query(self, sql: str, params: DbParams | None = None) -> list[DbRow]:
        from psycopg.rows import dict_row

        self._ensure_open()
        try:
            with self._pool.connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, params or ())
                    return list(cur.fetchall())
        except Exception as exc:  # noqa: BLE001 — surface as DatabaseError
            raise DatabaseError(str(exc)) from exc

    def query_one(self, sql: str, params: DbParams | None = None) -> DbRow | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: DbParams | None = None) -> int:
        self._ensure_open()
        try:
            with self._pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params or ())
                    conn.commit()
                    return cur.rowcount
        except Exception as exc:  # noqa: BLE001 — surface as DatabaseError
            raise DatabaseError(str(exc)) from exc

    def _ensure_open(self) -> None:
        if not self._opened:
            self.open()


def create_database_session(
    database_url: str | None,
    *,
    fallback: DatabaseSession | None = None,
    min_size: int = DEFAULT_POOL_MIN_SIZE,
    max_size: int = DEFAULT_POOL_MAX_SIZE,
    timeout: float = DEFAULT_POOL_TIMEOUT_SECONDS,
    open_timeout: float = DEFAULT_POOL_OPEN_TIMEOUT_SECONDS,
) -> DatabaseSession:
    """Build a database session from ``DATABASE_URL`` when a real URL is provided."""

    if database_url and not database_url.startswith("scaffold://"):
        return PostgresDatabaseSession(
            database_url=database_url,
            min_size=min_size,
            max_size=max_size,
            timeout=timeout,
            open_timeout=open_timeout,
        )
    return fallback or ScaffoldDatabaseSession()
