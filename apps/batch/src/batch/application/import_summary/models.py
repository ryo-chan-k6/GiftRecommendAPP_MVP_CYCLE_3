"""BATCH-017 Import Summary 作成 domain models (in-memory / scaffold).

物理書込 IF = IF-DB-BATCH-017（item_import_summary INSERT + ON CONFLICT DO NOTHING）。
IF-DB-BATCH-016 / IF-OBS-006 は物理書込に使わない。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

SourceApi = Literal["item_search", "item_ranking", "genre_search", "attribute_search"]
ImportSummaryRunStatus = Literal["succeeded", "partially_succeeded", "failed"]
DiffStatus = Literal["new", "updated", "unchanged", "unavailable"]


@dataclass(frozen=True)
class BatchRunLogRow:
    """batch_run_log 読取行（必須入力・書込禁止）。"""

    batch_run_id: str
    status: str = "succeeded"


@dataclass(frozen=True)
class ApiCallLogRow:
    """api_call_log 読取行（fetched_count 正本）。"""

    batch_run_id: str
    source_api: SourceApi
    item_count: int


@dataclass(frozen=True)
class ProductDiffRow:
    """product_diff_result 読取行（item_search 時の diff 件数）。"""

    batch_run_id: str
    source_api: SourceApi
    diff_status: DiffStatus


@dataclass(frozen=True)
class StagingItemRow:
    """staging_item 読取行（fetched_count 補完用）。"""

    batch_run_id: str
    source_api: SourceApi


@dataclass(frozen=True)
class FeatureEmbeddingProgress:
    """同一 Run の Feature / Embedding 完了フラグと件数。

    未完了・未実行は件数 0（仕様書 §9.3）。既存 Summary 行の UPDATE 埋め直しは行わない。
    """

    feature_completed: bool = False
    feature_generated_count: int = 0
    embedding_completed: bool = False
    embedding_generated_count: int = 0


@dataclass(frozen=True)
class SkipFailCounts:
    """BATCH-007 文脈の skipped / failed 件数（seed / 読取結果）。"""

    skipped_count: int = 0
    failed_count: int = 0


@dataclass(frozen=True)
class AggregatedCounts:
    """集計結果（INSERT 前）。"""

    fetched_count: int
    new_count: int
    updated_count: int
    unchanged_count: int
    unavailable_count: int
    skipped_count: int
    failed_count: int
    feature_generated_count: int
    embedding_generated_count: int


@dataclass(frozen=True)
class ImportSummaryInsertRow:
    """IF-DB-BATCH-017 INSERT 行。"""

    batch_run_id: str
    source: str
    source_api: SourceApi
    fetched_count: int
    new_count: int
    updated_count: int
    unchanged_count: int
    unavailable_count: int
    skipped_count: int
    failed_count: int
    feature_generated_count: int
    embedding_generated_count: int
    summarized_at: datetime


@dataclass
class ImportSummaryJobResult:
    batch_id: str
    job_run_id: str
    status: ImportSummaryRunStatus = "failed"
    completed_phases: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
    source_api: str | None = None
    insert_attempted: bool = False
    insert_applied: bool = False
    conflict_skipped: bool = False
    summary_row: ImportSummaryInsertRow | None = None
    # 隣接 IF 非書込カウンタ（常に 0）
    feature_metric_write_count: int = 0
    meaning_metric_write_count: int = 0
    normalization_metric_write_count: int = 0
    product_diff_write_count: int = 0
    staging_item_write_count: int = 0
    item_write_count: int = 0
