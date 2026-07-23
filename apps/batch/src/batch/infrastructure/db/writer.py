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

    @property
    def backend(self) -> str: ...

    def write_rows(self, table: str, rows: tuple[dict[str, object], ...]) -> DbWriteResult: ...

    def upsert_rows(
        self,
        table: str,
        rows: tuple[dict[str, object], ...],
        *,
        conflict_columns: tuple[str, ...],
        update_columns: tuple[str, ...] | None = None,
    ) -> DbWriteResult: ...


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


def _normalize_row_columns(rows: tuple[dict[str, object], ...]) -> tuple[str, ...]:
    if not rows:
        return ()
    columns = tuple(rows[0].keys())
    if not columns:
        raise DatabaseError("rows require at least one column")
    for column in columns:
        _assert_sql_ident(str(column), kind="column")
    for row in rows:
        if tuple(row.keys()) != columns:
            raise DatabaseError("all rows must share the same column set and order")
    return tuple(str(column) for column in columns)


@dataclass
class ScaffoldDbWriter:
    """Placeholder writer without a real database connection."""

    write_calls: list[dict[str, object]] = field(default_factory=list)
    upsert_calls: list[dict[str, object]] = field(default_factory=list)
    backend: str = "scaffold"

    def write_rows(self, table: str, rows: tuple[dict[str, object], ...]) -> DbWriteResult:
        self.write_calls.append({"table": table, "rows": rows})
        return DbWriteResult(rows_affected=len(rows), table=table)

    def upsert_rows(
        self,
        table: str,
        rows: tuple[dict[str, object], ...],
        *,
        conflict_columns: tuple[str, ...],
        update_columns: tuple[str, ...] | None = None,
    ) -> DbWriteResult:
        self.upsert_calls.append(
            {
                "table": table,
                "rows": rows,
                "conflict_columns": conflict_columns,
                "update_columns": update_columns,
            }
        )
        return DbWriteResult(rows_affected=len(rows), table=table)


@dataclass
class PostgresDbWriter:
    """PostgreSQL writer backed by psycopg.

    - ``write_rows``: multi-row INSERT
    - ``upsert_rows``: INSERT ... ON CONFLICT DO UPDATE（T4a）
    """

    database_url: str
    backend: str = "postgres"

    def write_rows(self, table: str, rows: tuple[dict[str, object], ...]) -> DbWriteResult:
        if not rows:
            return DbWriteResult(rows_affected=0, table=table)

        safe_table = _assert_sql_ident(table, kind="table")
        columns = _normalize_row_columns(rows)
        return self._execute_insert(safe_table, columns, rows)

    def upsert_rows(
        self,
        table: str,
        rows: tuple[dict[str, object], ...],
        *,
        conflict_columns: tuple[str, ...],
        update_columns: tuple[str, ...] | None = None,
    ) -> DbWriteResult:
        if not rows:
            return DbWriteResult(rows_affected=0, table=table)
        if not conflict_columns:
            raise DatabaseError("conflict_columns must not be empty")

        safe_table = _assert_sql_ident(table, kind="table")
        columns = _normalize_row_columns(rows)
        conflict = tuple(_assert_sql_ident(column, kind="column") for column in conflict_columns)
        for column in conflict:
            if column not in columns:
                raise DatabaseError(f"conflict column {column!r} missing from row payload")

        if update_columns is None:
            updates = tuple(column for column in columns if column not in conflict)
        else:
            updates = tuple(_assert_sql_ident(column, kind="column") for column in update_columns)
            for column in updates:
                if column not in columns:
                    raise DatabaseError(f"update column {column!r} missing from row payload")

        import psycopg
        from psycopg import sql

        column_idents = [sql.Identifier(column) for column in columns]
        placeholders = sql.SQL(", ").join(sql.Placeholder() * len(columns))
        values_list = sql.SQL(", ").join(
            sql.SQL("({})").format(placeholders) for _ in rows
        )
        conflict_idents = sql.SQL(", ").join(sql.Identifier(column) for column in conflict)

        if updates:
            set_clause = sql.SQL(", ").join(
                sql.SQL("{col} = EXCLUDED.{col}").format(col=sql.Identifier(column))
                for column in updates
            )
            on_conflict = sql.SQL(
                "ON CONFLICT ({conflict}) DO UPDATE SET {updates}"
            ).format(conflict=conflict_idents, updates=set_clause)
        else:
            on_conflict = sql.SQL("ON CONFLICT ({conflict}) DO NOTHING").format(
                conflict=conflict_idents
            )

        statement = sql.SQL(
            "INSERT INTO {table} ({columns}) VALUES {values} {on_conflict}"
        ).format(
            table=sql.Identifier(safe_table),
            columns=sql.SQL(", ").join(column_idents),
            values=values_list,
            on_conflict=on_conflict,
        )
        params: list[object] = []
        for row in rows:
            params.extend(row[column] for column in columns)

        return self._execute(statement, params, table=table, fallback_affected=len(rows))

    def _execute_insert(
        self,
        safe_table: str,
        columns: tuple[str, ...],
        rows: tuple[dict[str, object], ...],
    ) -> DbWriteResult:
        from psycopg import sql

        column_idents = [sql.Identifier(column) for column in columns]
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
        return self._execute(statement, params, table=safe_table, fallback_affected=len(rows))

    def _execute(
        self,
        statement: object,
        params: list[object],
        *,
        table: str,
        fallback_affected: int,
    ) -> DbWriteResult:
        import psycopg

        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(statement, params)
                    conn.commit()
                    affected = (
                        cur.rowcount
                        if cur.rowcount is not None and cur.rowcount >= 0
                        else fallback_affected
                    )
                    return DbWriteResult(rows_affected=affected, table=table)
        except DatabaseError:
            raise
        except Exception as exc:  # noqa: BLE001 — surface as DatabaseError
            raise DatabaseError(mask_database_url(str(exc))) from exc


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


def resolve_job_db_writer(*, scaffold_demo: bool, database_url: str | None) -> DbWriter:
    """Resolve DbWriter for CLI jobs.

    ``--scaffold-demo`` は常に Scaffold。それ以外は ``DATABASE_URL`` で切替。
    """

    if scaffold_demo:
        return ScaffoldDbWriter()
    return create_db_writer(database_url)
