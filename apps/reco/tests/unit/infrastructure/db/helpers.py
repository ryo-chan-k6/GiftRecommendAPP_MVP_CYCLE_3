"""Test helpers for infrastructure/db."""

from __future__ import annotations

from dataclasses import dataclass, field

from reco.infrastructure.db.session import DbRow, ScaffoldDatabaseSession


@dataclass
class ScriptedDatabaseSession(ScaffoldDatabaseSession):
    """Scaffold session that returns scripted query results in order."""

    scripted_query_results: list[list[DbRow]] = field(default_factory=list)
    _query_index: int = 0

    def query(self, sql: str, params=()):  # type: ignore[no-untyped-def]
        self._assert_available()
        bound = tuple(params or ())
        self.operations.append(("query", sql, bound))
        if self._query_index < len(self.scripted_query_results):
            rows = self.scripted_query_results[self._query_index]
            self._query_index += 1
            return list(rows)
        return list(self.query_rows)
