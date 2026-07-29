"""BATCH-017 Import Summary 作成ジョブ実装.

Phases（仕様書 §8.2）:
open_run → resolve_source_api → aggregate_fetched → aggregate_diff →
aggregate_skip_fail → aggregate_feature_embedding → persist_summary →
record_phase → finalize

モジュール主参照: **MOD-BATCH-047**（Item Import Summary Writer）。
一覧の Import Summary Builder は同義（追加採番なし）。

物理書込 IF = IF-DB-BATCH-017 のみ。
phase_log 物理名は `summary_created`。
冪等: INSERT + ON CONFLICT DO NOTHING（UPDATE しない）。

Wave 4: tracker は常に ``job_run_id``（BATCH-017 自身の新規 UUID）。
集計 / require_batch_run / insert_summary の ``batch_run_id`` は引数の既存 Run。
未指定時のみ ``job_run_id`` フォールバック（scaffold 用）。
"""

from __future__ import annotations

from datetime import UTC, datetime

import sys

from batch.application.import_summary.aggregator import (
    build_aggregated_counts,
    build_insert_row,
    resolve_source_api,
)
from batch.application.import_summary.models import BatchRunLogRow, ImportSummaryJobResult
from batch.application.import_summary.repositories import ImportSummaryRepositories
from batch.application.job_run import (
    PIPELINE_ITEM_MEANING_BATCH_NAME,
    JobRunTracker,
    ScaffoldJobRunTracker,
)
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger

BATCH_ID = "BATCH-017"
IMPORT_SUMMARY_PHASES: tuple[str, ...] = (
    "open_run",
    "resolve_source_api",
    "aggregate_fetched",
    "aggregate_diff",
    "aggregate_skip_fail",
    "aggregate_feature_embedding",
    "persist_summary",
    "record_phase",
    "finalize",
)
PHASE_SUMMARY_CREATED = "summary_created"


class ImportSummaryError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _is_batch_already_running(tracker: JobRunTracker) -> bool:
    records = getattr(tracker, "records", None)
    if not isinstance(records, list):
        return False
    starts = 0
    completes = 0
    for record in records:
        if getattr(record, "batch_id", None) != BATCH_ID:
            continue
        status = getattr(record, "status", None)
        if status == "running":
            starts += 1
        elif status in {"succeeded", "partially_succeeded", "failed"}:
            completes += 1
    return starts > completes


class ImportSummaryJob:
    """MOD-BATCH-047 Item Import Summary Writer オーケストレータ."""

    def __init__(
        self,
        *,
        repositories: ImportSummaryRepositories,
        job_run_tracker: JobRunTracker | None = None,
        logger: BatchLogger | None = None,
    ) -> None:
        self._repos = repositories
        self._tracker = job_run_tracker or ScaffoldJobRunTracker()
        self._logger = logger or ScaffoldBatchLogger()

    @property
    def repositories(self) -> ImportSummaryRepositories:
        """Expose repositories for CLI bind_run / observability wiring."""

        return self._repos

    def run(
        self,
        *,
        job_run_id: str,
        source_api: str | None = None,
        batch_run_id: str | None = None,
        trace_id: str | None = None,
        now: datetime | None = None,
    ) -> ImportSummaryJobResult:
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        _ = bound_logger
        # 集計対象は既存 Run。tracker は BATCH-017 自身の job_run_id（PK 衝突回避）。
        aggregate_run_id = (batch_run_id or "").strip() or job_run_id
        result = ImportSummaryJobResult(
            batch_id=BATCH_ID,
            job_run_id=job_run_id,
            status="failed",
        )

        if _is_batch_already_running(self._tracker):
            result.error_codes.append("GRS-BAT-003")
            self._repos.record_error(code="GRS-BAT-003", summary="batch already running")
            return result

        self._tracker.start(batch_id=BATCH_ID, job_run_id=job_run_id)
        result.completed_phases.append("open_run")

        try:
            # 複合子で上流が scaffold 等で pipeline 行未作成のとき ensure（#1726）。
            # 既に 003 等が作済みなら require のみ（ensure しない）。
            try:
                self._repos.require_batch_run(aggregate_run_id)
            except LookupError as missing_exc:
                if aggregate_run_id == job_run_id:
                    raise ImportSummaryError("GRS-VAL-001", str(missing_exc)) from missing_exc
                self._tracker.ensure_batch_run(
                    batch_id=PIPELINE_ITEM_MEANING_BATCH_NAME,
                    batch_run_id=aggregate_run_id,
                )
                print(
                    "pipeline batch_run_log ensure: "
                    f"batch_run_id={aggregate_run_id} "
                    f"batch_name={PIPELINE_ITEM_MEANING_BATCH_NAME}",
                    file=sys.stderr,
                )
                # scaffold（db_reader なし）では tracker ensure が repos に反映されないため追記
                if self._repos.db_reader is None and not any(
                    row.batch_run_id == aggregate_run_id for row in self._repos.batch_runs
                ):
                    self._repos.batch_runs.append(
                        BatchRunLogRow(batch_run_id=aggregate_run_id, status="running")
                    )
                try:
                    self._repos.require_batch_run(aggregate_run_id)
                except LookupError as exc:
                    raise ImportSummaryError("GRS-VAL-001", str(exc)) from exc

            raw_source = (source_api or "").strip() or None
            if raw_source is None:
                raw_source = self._repos.resolve_default_source_api()
            try:
                resolved = resolve_source_api(raw_source)
            except ValueError as exc:
                raise ImportSummaryError("GRS-CFG-001", str(exc)) from exc
            result.source_api = resolved
            result.completed_phases.append("resolve_source_api")

            api_calls = self._repos.load_api_calls(batch_run_id=aggregate_run_id)
            staging_items = self._repos.load_staging_items(batch_run_id=aggregate_run_id)
            result.completed_phases.append("aggregate_fetched")

            diffs = self._repos.load_diffs(batch_run_id=aggregate_run_id)
            result.completed_phases.append("aggregate_diff")

            skip_fail = self._repos.load_skip_fail()
            result.completed_phases.append("aggregate_skip_fail")

            progress = self._repos.load_feature_embedding_progress()
            result.completed_phases.append("aggregate_feature_embedding")

            ts = now or datetime.now(UTC)
            counts = build_aggregated_counts(
                api_calls=api_calls,
                diffs=diffs,
                staging_items=staging_items,
                skip_fail=skip_fail,
                progress=progress,
                batch_run_id=aggregate_run_id,
                source_api=resolved,
            )
            insert_row = build_insert_row(
                counts=counts,
                batch_run_id=aggregate_run_id,
                source_api=resolved,
                summarized_at=ts,
            )
            applied = self._repos.insert_summary(insert_row)
            result.insert_attempted = True
            result.insert_applied = applied
            result.conflict_skipped = not applied
            result.summary_row = insert_row
            result.completed_phases.append("persist_summary")

            result.feature_metric_write_count = self._repos.feature_metric_write_count
            result.meaning_metric_write_count = self._repos.meaning_metric_write_count
            result.normalization_metric_write_count = (
                self._repos.normalization_metric_write_count
            )
            result.product_diff_write_count = self._repos.product_diff_write_count
            result.staging_item_write_count = self._repos.staging_item_write_count
            result.item_write_count = self._repos.item_write_count

            return self._phase_finalize(result)
        except ImportSummaryError as exc:
            result.error_codes.append(exc.code)
            self._repos.record_error(code=exc.code, summary=exc.message)
            self._tracker.complete(
                batch_id=BATCH_ID, job_run_id=job_run_id, status="failed"
            )
            result.completed_phases.append("finalize")
            result.status = "failed"
            return result
        except Exception:
            self._tracker.complete(
                batch_id=BATCH_ID, job_run_id=job_run_id, status="failed"
            )
            raise

    def _phase_finalize(self, result: ImportSummaryJobResult) -> ImportSummaryJobResult:
        if result.insert_attempted:
            result.status = "succeeded"
            tracker_status = "succeeded"
        else:
            result.status = "failed"
            if "GRS-BAT-001" not in result.error_codes:
                result.error_codes.append("GRS-BAT-001")
            tracker_status = "failed"

        self._repos.record_phase(phase=PHASE_SUMMARY_CREATED, status=tracker_status)
        result.completed_phases.append("record_phase")

        self._tracker.complete(
            batch_id=BATCH_ID,
            job_run_id=result.job_run_id,
            status=tracker_status,
        )
        result.completed_phases.append("finalize")
        return result
