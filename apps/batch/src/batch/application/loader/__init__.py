"""Loader phase scaffold."""

from __future__ import annotations

from batch.application.context import BatchJobContext
from batch.infrastructure.db import DbWriter, ScaffoldDbWriter


class LoaderStep:
    """Phase4a scaffold: persist transformed records via infrastructure writer."""

    phase = "loader"

    def __init__(self, db_writer: DbWriter | None = None) -> None:
        self._db_writer = db_writer or ScaffoldDbWriter()

    def execute(self, context: BatchJobContext) -> BatchJobContext:
        rows = tuple(context.transformed_records or ())
        result = self._db_writer.write_rows("staging_item", rows)
        context.loaded_row_count = result.rows_affected
        context.completed_phases.append(self.phase)
        return context
