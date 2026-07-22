"""Database writer boundary for batch loaders."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

_SENSITIVE_URL_PATTERN = re.compile(
    r"(postgres(?:ql)?://)([^:@/]+)(?::([^@/]*))?@",
    re.IGNORECASE,
)
_IDENT_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")


@dataclass(frozen=True)
class DbWriteResult:
    """Result of a batch write operation."""

    rows_affected: int
    table: str


class DatabaseError(RuntimeError):
    """Raised when a database writer operation fails."""


class DbWriter(Protocol):
    """Database write boundary for batch loaders."""

    def write_rows(self, table: str, rows: tuple[dict[str, object], ...]) -> DbWriteResult: ...


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


def _assert_sql_ident(name: str, *, kind: str) -> str:
    if not _IDENT_PATTERN.fullmatch(name):
        raise DatabaseError(f"invalid SQL {kind} identifier: {name!r}")
    return name


@dataclass
class ScaffoldDbWriter:
    """Placeholder writer without a real database connection."""

    write_calls: list[dict[str, object]] = field(default_factory=list)

    def write_rows(self, table: str, rows: tuple[dict[str, object], ...]) -> DbWriteResult:
        self.write_calls.append({"table": table, "rows": rows})
        return DbWriteResult(rows_affected=len(rows), table=table)


@dataclass
class PostgresDbWriter:
    """PostgreSQL writer backed by psycopg (parameterized INSERT).

    T3 foundation: generic multi-row INSERT for ``write_rows``.
    Table-specific UPSERT / conflict 方針は T4（IF stub 解除）で repositories 側に実装する。
    """

    database_url: str
    backend: str = "postgres"

    def write_rows(self, table: str, rows: tuple[dict[str, object], ...]) -> DbWriteResult:
        if not rows:
            return DbWriteResult(rows_affected=0, table=table)

        safe_table = _assert_sql_ident(table, kind="table")
        columns = tuple(rows[0].keys())
        if not columns:
            raise DatabaseError("write_rows requires at least one column")
        for column in columns:
            _assert_sql_ident(str(column), kind="column")

        for row in rows:
            if tuple(row.keys()) != columns:
                raise DatabaseError("all rows must share the same column set and order")

        import psycopg
        from psycopg import sql

        column_idents = [sql.Identifier(str(column)) for column in columns]
        placeholders = sql.SQL(", ").join(sql.Placeholder() * len(columns))
        values_list = sql.SQL(", ").join(
            sql.SQL("({})").format(placeholders) for _ in rows
        )
        statement = sql.SQL("INSERT INTO {table} ({columns}) VALUES {values}").format(
            table=sql.Identifier(safe_table),
            columns=sql.SQL(", ").join(column_idents),
            values=values_list,
        )
        params: list[object] = []
        for row in rows:
            params.extend(row[column] for column in columns)

        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(statement, params)
                    conn.commit()
                    affected = cur.rowcount if cur.rowcount and cur.rowcount > 0 else len(rows)
                    return DbWriteResult(rows_affected=affected, table=table)
        except DatabaseError:
            raise
        except Exception as exc:  # noqa: BLE001 — surface as DatabaseError
            # 例外メッセージに接続文字列が混ざる場合があるため、呼び出し側は mask して扱うこと
            raise DatabaseError(str(exc)) from exc


def create_db_writer(
    database_url: str | None,
    *,
    fallback: DbWriter | None = None,
) -> DbWriter:
    """Build a DbWriter from ``DATABASE_URL`` when a real URL is provided.

    - unset / empty / ``scaffold://...`` → ScaffoldDbWriter（または fallback）
    - それ以外 → PostgresDbWriter
    """

    if database_url and not database_url.startswith("scaffold://"):
        return PostgresDbWriter(database_url=database_url)
    return fallback or ScaffoldDbWriter()
