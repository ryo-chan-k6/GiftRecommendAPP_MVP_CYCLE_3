"""Database reader boundary for batch loaders."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from batch.infrastructure.db.writer import DatabaseError, mask_database_url

_IDENT_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")


@dataclass(frozen=True)
class DbReadResult:
    """Result of a batch read operation."""

    rows: tuple[dict[str, object], ...]
    table: str

    @property
    def row_count(self) -> int:
        return len(self.rows)


class DbReader(Protocol):
    """Database read boundary for batch loaders.

    Arbitrary SQL strings are intentionally unsupported. Callers select by
    validated table / column identifiers and equality filters only.
    """

    @property
    def backend(self) -> str: ...

    def fetch_rows(
        self,
        table: str,
        *,
        columns: tuple[str, ...],
        equals: tuple[tuple[str, object], ...] = (),
        order_by: tuple[str, ...] = (),
        limit: int | None = None,
    ) -> DbReadResult: ...


def _assert_sql_ident(name: str, *, kind: str) -> str:
    if not _IDENT_PATTERN.fullmatch(name):
        raise DatabaseError(f"invalid SQL {kind} identifier: {name!r}")
    return name


def _validate_fetch_args(
    table: str,
    *,
    columns: tuple[str, ...],
    equals: tuple[tuple[str, object], ...],
    order_by: tuple[str, ...],
    limit: int | None,
) -> tuple[str, tuple[str, ...], tuple[tuple[str, object], ...], tuple[str, ...], int | None]:
    safe_table = _assert_sql_ident(table, kind="table")
    if not columns:
        raise DatabaseError("columns require at least one column")
    safe_columns = tuple(_assert_sql_ident(column, kind="column") for column in columns)
    safe_equals: list[tuple[str, object]] = []
    for column, value in equals:
        safe_equals.append((_assert_sql_ident(column, kind="column"), value))
    safe_order_by = tuple(_assert_sql_ident(column, kind="column") for column in order_by)
    if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool) or limit < 1):
        raise DatabaseError(f"limit must be a positive int, got {limit!r}")
    return safe_table, safe_columns, tuple(safe_equals), safe_order_by, limit


@dataclass
class ScaffoldDbReader:
    """In-memory reader for scaffold / unit tests."""

    seed_rows: dict[str, tuple[dict[str, object], ...]] = field(default_factory=dict)
    fetch_calls: list[dict[str, object]] = field(default_factory=list)
    backend: str = "scaffold"

    def seed(self, table: str, rows: tuple[dict[str, object], ...]) -> None:
        self.seed_rows[table] = rows

    def fetch_rows(
        self,
        table: str,
        *,
        columns: tuple[str, ...],
        equals: tuple[tuple[str, object], ...] = (),
        order_by: tuple[str, ...] = (),
        limit: int | None = None,
    ) -> DbReadResult:
        safe_table, safe_columns, safe_equals, safe_order_by, safe_limit = _validate_fetch_args(
            table,
            columns=columns,
            equals=equals,
            order_by=order_by,
            limit=limit,
        )
        self.fetch_calls.append(
            {
                "table": safe_table,
                "columns": safe_columns,
                "equals": safe_equals,
                "order_by": safe_order_by,
                "limit": safe_limit,
            }
        )
        rows = list(self.seed_rows.get(safe_table, ()))
        for column, value in safe_equals:
            rows = [row for row in rows if row.get(column) == value]
        if safe_order_by:
            rows.sort(
                key=lambda row: tuple(
                    (row.get(column) is None, str(row.get(column))) for column in safe_order_by
                )
            )
        if safe_limit is not None:
            rows = rows[:safe_limit]
        projected = tuple({column: row.get(column) for column in safe_columns} for row in rows)
        return DbReadResult(rows=projected, table=safe_table)


@dataclass(frozen=True)
class PostgresDbReader:
    """PostgreSQL reader backed by psycopg."""

    database_url: str
    backend: str = "postgres"

    def fetch_rows(
        self,
        table: str,
        *,
        columns: tuple[str, ...],
        equals: tuple[tuple[str, object], ...] = (),
        order_by: tuple[str, ...] = (),
        limit: int | None = None,
    ) -> DbReadResult:
        safe_table, safe_columns, safe_equals, safe_order_by, safe_limit = _validate_fetch_args(
            table,
            columns=columns,
            equals=equals,
            order_by=order_by,
            limit=limit,
        )
        from psycopg import sql
        from psycopg.rows import dict_row

        column_idents = [sql.Identifier(column) for column in safe_columns]
        statement = sql.SQL("SELECT {columns} FROM {table}").format(
            columns=sql.SQL(", ").join(column_idents),
            table=sql.Identifier(safe_table),
        )
        params: list[object] = []
        if safe_equals:
            predicates = [
                sql.SQL("{column} = {placeholder}").format(
                    column=sql.Identifier(column),
                    placeholder=sql.Placeholder(),
                )
                for column, _value in safe_equals
            ]
            statement = sql.SQL("{base} WHERE {where}").format(
                base=statement,
                where=sql.SQL(" AND ").join(predicates),
            )
            params.extend(value for _column, value in safe_equals)
        if safe_order_by:
            statement = sql.SQL("{base} ORDER BY {order}").format(
                base=statement,
                order=sql.SQL(", ").join(sql.Identifier(column) for column in safe_order_by),
            )
        if safe_limit is not None:
            statement = sql.SQL("{base} LIMIT {limit}").format(
                base=statement,
                limit=sql.Literal(safe_limit),
            )

        import psycopg

        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(statement, params)
                    fetched = cur.fetchall()
                    rows = tuple(dict(row) for row in fetched)
                    return DbReadResult(rows=rows, table=safe_table)
        except DatabaseError:
            raise
        except Exception as exc:  # noqa: BLE001 — surface as DatabaseError
            raise DatabaseError(mask_database_url(str(exc))) from exc


def create_db_reader(
    database_url: str | None,
    *,
    fallback: DbReader | None = None,
) -> DbReader:
    """Build a DbReader from ``DATABASE_URL`` when a real URL is provided.

    - unset / empty / ``scaffold://...`` → ScaffoldDbReader（または fallback）
    - それ以外 → PostgresDbReader
    """

    if database_url and not database_url.startswith("scaffold://"):
        return PostgresDbReader(database_url=database_url)
    return fallback or ScaffoldDbReader()


def resolve_job_db_reader(*, scaffold_demo: bool, database_url: str | None) -> DbReader:
    """Resolve DbReader for CLI jobs.

    ``--scaffold-demo`` は常に Scaffold。それ以外は ``DATABASE_URL`` で切替。
    """

    if scaffold_demo:
        return ScaffoldDbReader()
    return create_db_reader(database_url)


def is_live_db_reader(reader: DbReader) -> bool:
    """Return True when the reader talks to a real Postgres backend."""

    return reader.backend == "postgres"
