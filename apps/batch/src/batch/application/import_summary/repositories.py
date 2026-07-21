"""In-memory repositories for BATCH-017 scaffold / UT.

- batch_run_log / api_call_log / product_diff_result / staging_item READ ONLY
- item_import_summary INSERT + ON CONFLICT DO NOTHING（IF-DB-BATCH-017）のみ書込
- UPDATE 経路なし
- IF-DB-BATCH-016（3 Metric）/ 業務明細テーブルは非書込
"""

from __future__ import annotations

from dataclasses import dataclass, field

from batch.application.import_summary.models import (
    ApiCallLogRow,
    BatchRunLogRow,
    FeatureEmbeddingProgress,
    ImportSummaryInsertRow,
    ProductDiffRow,
    SkipFailCounts,
    SourceApi,
    StagingItemRow,
)
from batch.infrastructure.db import DbWriter


def _summary_key(row: ImportSummaryInsertRow) -> tuple[str, str]:
    """UNIQUE (batch_run_id, source_api)。"""

    return (row.batch_run_id, row.source_api)


@dataclass
class ImportSummaryRepositories:
    """Facade: 入力読取 / IF-DB-BATCH-017 INSERT / phase・error logs."""

    db_writer: DbWriter
    seed_batch_runs: list[BatchRunLogRow] = field(default_factory=list)
    seed_api_calls: list[ApiCallLogRow] = field(default_factory=list)
    seed_diffs: list[ProductDiffRow] = field(default_factory=list)
    seed_staging_items: list[StagingItemRow] = field(default_factory=list)
    seed_skip_fail: SkipFailCounts = field(default_factory=SkipFailCounts)
    seed_feature_embedding: FeatureEmbeddingProgress = field(
        default_factory=FeatureEmbeddingProgress
    )
    seed_default_source_api: SourceApi | None = "item_search"

    batch_runs: list[BatchRunLogRow] = field(default_factory=list)
    api_calls: list[ApiCallLogRow] = field(default_factory=list)
    diffs: list[ProductDiffRow] = field(default_factory=list)
    staging_items: list[StagingItemRow] = field(default_factory=list)
    skip_fail: SkipFailCounts = field(default_factory=SkipFailCounts)
    feature_embedding: FeatureEmbeddingProgress = field(
        default_factory=FeatureEmbeddingProgress
    )
    default_source_api: SourceApi | None = None

    summary_rows: list[ImportSummaryInsertRow] = field(default_factory=list)
    insert_attempt_count: int = 0
    insert_applied_count: int = 0
    conflict_skip_count: int = 0

    # 隣接 IF / 業務明細 非書込カウンタ（常に 0）
    feature_metric_write_count: int = 0
    meaning_metric_write_count: int = 0
    normalization_metric_write_count: int = 0
    product_diff_write_count: int = 0
    staging_item_write_count: int = 0
    item_write_count: int = 0
    summary_update_count: int = 0

    phase_logs: list[dict[str, object]] = field(default_factory=list)
    error_logs: list[dict[str, object]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.batch_runs = list(self.seed_batch_runs)
        self.api_calls = list(self.seed_api_calls)
        self.diffs = list(self.seed_diffs)
        self.staging_items = list(self.seed_staging_items)
        self.skip_fail = self.seed_skip_fail
        self.feature_embedding = self.seed_feature_embedding
        self.default_source_api = self.seed_default_source_api

    def require_batch_run(self, batch_run_id: str) -> BatchRunLogRow:
        for row in self.batch_runs:
            if row.batch_run_id == batch_run_id:
                return row
        raise LookupError(f"batch_run_log not found: {batch_run_id}")

    def resolve_default_source_api(self) -> SourceApi | None:
        return self.default_source_api

    def load_api_calls(self, *, batch_run_id: str) -> tuple[ApiCallLogRow, ...]:
        return tuple(row for row in self.api_calls if row.batch_run_id == batch_run_id)

    def load_diffs(self, *, batch_run_id: str) -> tuple[ProductDiffRow, ...]:
        return tuple(row for row in self.diffs if row.batch_run_id == batch_run_id)

    def load_staging_items(self, *, batch_run_id: str) -> tuple[StagingItemRow, ...]:
        return tuple(
            row for row in self.staging_items if row.batch_run_id == batch_run_id
        )

    def load_skip_fail(self) -> SkipFailCounts:
        return self.skip_fail

    def load_feature_embedding_progress(self) -> FeatureEmbeddingProgress:
        return self.feature_embedding

    def insert_summary(self, row: ImportSummaryInsertRow) -> bool:
        """IF-DB-BATCH-017: INSERT + ON CONFLICT DO NOTHING。

        Returns:
            True if a new row was inserted, False if conflict skipped (DO NOTHING).
        """

        self.insert_attempt_count += 1
        key = _summary_key(row)
        existing_keys = {_summary_key(existing) for existing in self.summary_rows}
        if key in existing_keys:
            self.conflict_skip_count += 1
            self.db_writer.write_rows(
                "item_import_summary",
                (self._row_payload(row, conflict_skipped=True),),
            )
            return False

        self.summary_rows.append(row)
        self.insert_applied_count += 1
        self.db_writer.write_rows(
            "item_import_summary",
            (self._row_payload(row, conflict_skipped=False),),
        )
        return True

    def record_phase(self, *, phase: str, status: str) -> None:
        """物理 phase_log。Import Summary 完了は summary_created。"""

        self.phase_logs.append({"phase": phase, "status": status})

    def record_error(self, *, code: str, summary: str) -> None:
        self.error_logs.append({"code": code, "summary": summary})

    @staticmethod
    def _row_payload(
        row: ImportSummaryInsertRow, *, conflict_skipped: bool
    ) -> dict[str, object]:
        return {
            "batch_run_id": row.batch_run_id,
            "source": row.source,
            "source_api": row.source_api,
            "fetched_count": row.fetched_count,
            "new_count": row.new_count,
            "updated_count": row.updated_count,
            "unchanged_count": row.unchanged_count,
            "unavailable_count": row.unavailable_count,
            "skipped_count": row.skipped_count,
            "failed_count": row.failed_count,
            "feature_generated_count": row.feature_generated_count,
            "embedding_generated_count": row.embedding_generated_count,
            "summarized_at": row.summarized_at.isoformat(),
            "op": "if_db_batch_017_insert",
            "conflict_skipped": conflict_skipped,
        }
