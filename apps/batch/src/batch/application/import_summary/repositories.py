"""Repositories for BATCH-017 Import Summary 作成.

``require_batch_run`` / ``load_api_calls`` / ``load_diffs`` / ``load_staging_items``
は ``DbReader`` 経由（Wave G）。

``load_skip_fail`` / ``load_feature_embedding_progress`` は E4 観測横断が必要のため
seed / 0 埋めを維持（フル配線は out of scope）。

``item_import_summary`` INSERT SQL 本格化は out of scope（scaffold / stub 書込のみ）。

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
    DiffStatus,
    FeatureEmbeddingProgress,
    ImportSummaryInsertRow,
    ProductDiffRow,
    SkipFailCounts,
    SourceApi,
    StagingItemRow,
)
from batch.infrastructure.db import DbReader, DbWriter

_BATCH_RUN_COLUMNS = (
    "batch_run_id",
    "run_status",
)
_API_CALL_COLUMNS = (
    "api_call_log_id",
    "batch_run_id",
    "source_api",
    "item_count",
)
_DIFF_COLUMNS = (
    "product_diff_result_id",
    "batch_run_id",
    "staging_item_id",
    "diff_status",
)
_RAW_METADATA_COLUMNS = (
    "raw_metadata_id",
    "api_call_log_id",
    "source_api",
)
_STAGING_COLUMNS = (
    "staging_item_id",
    "raw_metadata_id",
)


def _summary_key(row: ImportSummaryInsertRow) -> tuple[str, str]:
    """UNIQUE (batch_run_id, source_api)。"""

    return (row.batch_run_id, row.source_api)


def _as_source_api(value: object | None, *, fallback: SourceApi = "item_search") -> SourceApi:
    text = str(value or "").strip()
    if text in {"item_search", "item_ranking", "genre_search", "attribute_search"}:
        return text  # type: ignore[return-value]
    return fallback


def _as_diff_status(value: object | None) -> DiffStatus:
    text = str(value or "").strip()
    if text in {"new", "updated", "unchanged", "unavailable"}:
        return text  # type: ignore[return-value]
    return "unavailable"


@dataclass
class ImportSummaryRepositories:
    """Facade: 入力読取 / IF-DB-BATCH-017 INSERT / phase・error logs."""

    db_writer: DbWriter
    db_reader: DbReader | None = None
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
        if self.db_reader is not None:
            result = self.db_reader.fetch_rows(
                "batch_run_log",
                columns=_BATCH_RUN_COLUMNS,
                equals=(("batch_run_id", batch_run_id),),
                limit=1,
            )
            if not result.rows:
                raise LookupError(f"batch_run_log not found: {batch_run_id}")
            row = result.rows[0]
            return BatchRunLogRow(
                batch_run_id=str(row["batch_run_id"]),
                status=str(row.get("run_status") or "succeeded"),
            )
        for row in self.batch_runs:
            if row.batch_run_id == batch_run_id:
                return row
        raise LookupError(f"batch_run_log not found: {batch_run_id}")

    def resolve_default_source_api(self) -> SourceApi | None:
        return self.default_source_api

    def load_api_calls(self, *, batch_run_id: str) -> tuple[ApiCallLogRow, ...]:
        if self.db_reader is not None:
            result = self.db_reader.fetch_rows(
                "api_call_log",
                columns=_API_CALL_COLUMNS,
                equals=(("batch_run_id", batch_run_id),),
                order_by=("api_call_log_id",),
            )
            return tuple(
                ApiCallLogRow(
                    batch_run_id=str(row["batch_run_id"]),
                    source_api=_as_source_api(row.get("source_api")),
                    item_count=int(row.get("item_count") or 0),
                )
                for row in result.rows
            )
        return tuple(row for row in self.api_calls if row.batch_run_id == batch_run_id)

    def load_diffs(self, *, batch_run_id: str) -> tuple[ProductDiffRow, ...]:
        if self.db_reader is not None:
            # product_diff_result に source_api 列は無い。Run 既定 source_api を stamp。
            # JOIN / OR 拡張は out of scope。
            fallback = self.default_source_api or "item_search"
            result = self.db_reader.fetch_rows(
                "product_diff_result",
                columns=_DIFF_COLUMNS,
                equals=(("batch_run_id", batch_run_id),),
                order_by=("product_diff_result_id",),
            )
            return tuple(
                ProductDiffRow(
                    batch_run_id=str(row["batch_run_id"]),
                    source_api=fallback,
                    diff_status=_as_diff_status(row.get("diff_status")),
                )
                for row in result.rows
            )
        return tuple(row for row in self.diffs if row.batch_run_id == batch_run_id)

    def load_staging_items(self, *, batch_run_id: str) -> tuple[StagingItemRow, ...]:
        if self.db_reader is not None:
            return self._load_staging_items_from_db(batch_run_id=batch_run_id)
        return tuple(
            row for row in self.staging_items if row.batch_run_id == batch_run_id
        )

    def load_skip_fail(self) -> SkipFailCounts:
        # BATCH-007 文脈の skip/fail 横断集計は E4 観測が必要。Wave G では seed / 0 埋め。
        return self.skip_fail

    def load_feature_embedding_progress(self) -> FeatureEmbeddingProgress:
        # Feature / Embedding 完了横断は E4。Wave G では seed / 0 埋めを維持。
        return self.feature_embedding

    def insert_summary(self, row: ImportSummaryInsertRow) -> bool:
        """IF-DB-BATCH-017: INSERT + ON CONFLICT DO NOTHING.

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

    def _load_staging_items_from_db(self, *, batch_run_id: str) -> tuple[StagingItemRow, ...]:
        """staging_item に batch_run_id / source_api 列は無いため equals 連鎖で辿る.

        api_call_log(batch_run_id) → raw_product_metadata(api_call_log_id)
        → staging_item(raw_metadata_id)。JOIN 拡張は使わない。
        """

        reader = self.db_reader
        assert reader is not None
        api_calls = reader.fetch_rows(
            "api_call_log",
            columns=("api_call_log_id", "source_api"),
            equals=(("batch_run_id", batch_run_id),),
        )
        rows: list[StagingItemRow] = []
        for call in api_calls.rows:
            call_id = call.get("api_call_log_id")
            if call_id is None:
                continue
            call_source = _as_source_api(
                call.get("source_api"),
                fallback=self.default_source_api or "item_search",
            )
            metas = reader.fetch_rows(
                "raw_product_metadata",
                columns=_RAW_METADATA_COLUMNS,
                equals=(("api_call_log_id", call_id),),
            )
            for meta in metas.rows:
                meta_id = meta.get("raw_metadata_id")
                if meta_id is None:
                    continue
                source_api = _as_source_api(meta.get("source_api"), fallback=call_source)
                staging = reader.fetch_rows(
                    "staging_item",
                    columns=_STAGING_COLUMNS,
                    equals=(("raw_metadata_id", meta_id),),
                )
                for _item in staging.rows:
                    rows.append(
                        StagingItemRow(batch_run_id=batch_run_id, source_api=source_api)
                    )
        return tuple(rows)

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
