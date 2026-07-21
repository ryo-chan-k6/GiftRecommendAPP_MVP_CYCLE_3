"""BATCH-019 Feedback分析ジョブ実装.

Phases（仕様書 §8.2 / §12）:
open_run → validate_input → resolve_feedback → classify → aggregate →
persist_analysis → finalize

モジュール:
- MOD-BATCH-042 Feedback Analyzer（本ジョブ + analyzer 内部責務）
- MOD-BATCH-043 / 044 は out of scope

IF-DB-BATCH-019 = 論理契約（scaffold: in-memory / stub）。
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from batch.application.feedback_analysis.analyzer import (
    aggregate_metrics,
    build_negative_trend_payload,
    build_period_aggregate_payload,
    build_type_breakdown_payload,
    classify_feedbacks,
)
from batch.application.feedback_analysis.models import (
    DEFAULT_AGGREGATION_SCOPE,
    DEFAULT_NEGATIVE_RATING_THRESHOLD,
    NEGATIVE_FEEDBACK_TYPES,
    FeedbackAnalysisJobResult,
    FeedbackAnalysisResultRow,
    RecommendationFeedbackRow,
)
from batch.application.feedback_analysis.repositories import (
    FeedbackAnalysisRepositories,
)
from batch.application.job_run import JobRunTracker, ScaffoldJobRunTracker
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger

BATCH_ID = "BATCH-019"
FEEDBACK_ANALYSIS_PHASES: tuple[str, ...] = (
    "open_run",
    "validate_input",
    "resolve_feedback",
    "classify",
    "aggregate",
    "persist_analysis",
    "finalize",
)
PHASE_ANALYSIS_COMPLETED = "analysis_completed"


class FeedbackAnalysisError(Exception):
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


def _parse_feedback_types(raw: str | None) -> frozenset[str] | None:
    if raw is None or raw.strip() == "":
        return None
    values = {part.strip() for part in raw.split(",") if part.strip()}
    return frozenset(values) if values else None


class FeedbackAnalysisJob:
    """MOD-BATCH-042 Feedback Analyzer オーケストレータ."""

    def __init__(
        self,
        *,
        repositories: FeedbackAnalysisRepositories,
        job_run_tracker: JobRunTracker | None = None,
        logger: BatchLogger | None = None,
    ) -> None:
        self._repos = repositories
        self._tracker = job_run_tracker or ScaffoldJobRunTracker()
        self._logger = logger or ScaffoldBatchLogger()

    def run(
        self,
        *,
        job_run_id: str,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        aggregation_scope: str | None = None,
        feedback_types: str | None = None,
        semantic_config_version_id: str | None = None,
        dry_run: bool = False,
        max_feedback_rows: int | None = None,
        negative_rating_threshold: int = DEFAULT_NEGATIVE_RATING_THRESHOLD,
        trace_id: str | None = None,
        now: datetime | None = None,
    ) -> FeedbackAnalysisJobResult:
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        _ = bound_logger
        ts = now or datetime.now(UTC)
        scope = (aggregation_scope or "").strip() or DEFAULT_AGGREGATION_SCOPE
        result = FeedbackAnalysisJobResult(
            batch_id=BATCH_ID,
            job_run_id=job_run_id,
            status="failed",
            dry_run=dry_run,
            period_start=period_start,
            period_end=period_end,
            aggregation_scope=scope,
        )

        if _is_batch_already_running(self._tracker):
            result.error_codes.append("GRS-BAT-003")
            self._repos.record_error(code="GRS-BAT-003", summary="batch already running")
            return result

        self._tracker.start(batch_id=BATCH_ID, job_run_id=job_run_id)
        result.completed_phases.append("open_run")

        try:
            self._phase_validate(period_start=period_start, period_end=period_end)
            result.completed_phases.append("validate_input")

            type_filter = _parse_feedback_types(feedback_types)
            rows = self._repos.load_feedbacks(
                period_start=period_start,
                period_end=period_end,
                feedback_types=type_filter,
                max_feedback_rows=max_feedback_rows,
            )
            result.feedback_resolved_count = len(rows)
            result.completed_phases.append("resolve_feedback")
            self._repos.record_phase(phase="feedback_resolved", status="succeeded")

            negatives, _others = classify_feedbacks(
                rows, rating_threshold=negative_rating_threshold
            )
            result.negative_count = len(negatives)
            result.completed_phases.append("classify")
            self._repos.record_phase(phase="classified", status="succeeded")

            metrics = aggregate_metrics(
                rows,
                negatives=negatives,
                period_start=period_start,
                period_end=period_end,
                aggregation_scope=scope,
                rating_threshold=negative_rating_threshold,
            )
            result.completed_phases.append("aggregate")
            self._repos.record_phase(phase="aggregated", status="succeeded")

            stub_rows = self._build_stub_rows(
                rows=rows,
                metrics=metrics,
                job_run_id=job_run_id,
                analyzed_at=ts,
                aggregation_scope=scope,
                period_start=period_start,
                period_end=period_end,
                semantic_config_version_id=semantic_config_version_id,
                negative_rating_threshold=negative_rating_threshold,
            )

            if not dry_run:
                persisted = self._repos.stub_persist_analysis_results(stub_rows)
                result.results_stubbed = len(persisted)
            else:
                result.results_stubbed = 0

            result.feedback_write_count = self._repos.feedback_write_count
            result.feedback_update_count = self._repos.feedback_update_count
            result.real_db_insert_count = self._repos.real_db_insert_count
            result.completed_phases.append("persist_analysis")
            self._repos.record_phase(phase="analysis_persisted", status="succeeded")

            return self._phase_finalize(result)
        except FeedbackAnalysisError as exc:
            result.error_codes.append(exc.code)
            self._repos.record_error(code=exc.code, summary=exc.message)
            self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
            result.completed_phases.append("finalize")
            result.status = "failed"
            return result
        except Exception:
            self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
            raise

    def _phase_validate(
        self,
        *,
        period_start: datetime | None,
        period_end: datetime | None,
    ) -> None:
        if period_start is not None and period_end is not None and period_start > period_end:
            raise FeedbackAnalysisError(
                "GRS-VAL-001",
                f"invalid period: start={period_start.isoformat()} end={period_end.isoformat()}",
            )

    def _build_stub_rows(
        self,
        *,
        rows: tuple[RecommendationFeedbackRow, ...],
        metrics: dict[str, object],
        job_run_id: str,
        analyzed_at: datetime,
        aggregation_scope: str,
        period_start: datetime | None,
        period_end: datetime | None,
        semantic_config_version_id: str | None,
        negative_rating_threshold: int,
    ) -> tuple[FeedbackAnalysisResultRow, ...]:
        """集計サマリ行 + Feedback 単位の type_breakdown 参照用スタブ.

        論理ERは Feedback 単位行も想定するが、scaffold は集計 JSON 中心。
        メトリクスはすべて analysis_result_json 内包。
        """

        semantic_id = (semantic_config_version_id or "").strip() or None
        period_row = FeedbackAnalysisResultRow(
            feedback_analysis_result_id=str(uuid4()),
            recommendation_feedback_id=None,
            analysis_type="period_aggregate",
            analysis_result_json=build_period_aggregate_payload(
                metrics=metrics, job_run_id=job_run_id
            ),
            analyzed_at=analyzed_at,
            batch_run_id=job_run_id,
            aggregation_scope=aggregation_scope,
            period_start=period_start,
            period_end=period_end,
            semantic_config_version_id=semantic_id,
        )
        type_row = FeedbackAnalysisResultRow(
            feedback_analysis_result_id=str(uuid4()),
            recommendation_feedback_id=None,
            analysis_type="type_breakdown",
            analysis_result_json=build_type_breakdown_payload(
                metrics=metrics, job_run_id=job_run_id
            ),
            analyzed_at=analyzed_at,
            batch_run_id=job_run_id,
            aggregation_scope=aggregation_scope,
            period_start=period_start,
            period_end=period_end,
            semantic_config_version_id=semantic_id,
        )
        negative_row = FeedbackAnalysisResultRow(
            feedback_analysis_result_id=str(uuid4()),
            recommendation_feedback_id=None,
            analysis_type="negative_trend",
            analysis_result_json=build_negative_trend_payload(
                metrics=metrics, job_run_id=job_run_id
            ),
            analyzed_at=analyzed_at,
            batch_run_id=job_run_id,
            aggregation_scope=aggregation_scope,
            period_start=period_start,
            period_end=period_end,
            semantic_config_version_id=semantic_id,
        )
        # Feedback 単位の参照行（空でも 0 件で成功。PII コメントは載せない）
        per_feedback: list[FeedbackAnalysisResultRow] = []
        for row in rows:
            is_neg = (
                row.feedback_type in NEGATIVE_FEEDBACK_TYPES
                or row.feedback_rating <= negative_rating_threshold
            )
            per_feedback.append(
                FeedbackAnalysisResultRow(
                    feedback_analysis_result_id=str(uuid4()),
                    recommendation_feedback_id=row.recommendation_feedback_id,
                    analysis_type="type_breakdown",
                    analysis_result_json={
                        "summary": "feedback_unit",
                        "feedback_type": row.feedback_type,
                        "feedback_target_type": row.feedback_target_type,
                        "feedback_rating": row.feedback_rating,
                        "metrics": {"is_negative": is_neg},
                    },
                    analyzed_at=analyzed_at,
                    batch_run_id=job_run_id,
                    aggregation_scope=aggregation_scope,
                    period_start=period_start,
                    period_end=period_end,
                    semantic_config_version_id=semantic_id,
                )
            )
        return (period_row, type_row, negative_row, *per_feedback)

    def _phase_finalize(
        self, result: FeedbackAnalysisJobResult
    ) -> FeedbackAnalysisJobResult:
        # Feedback 0 件でも空 stub で成功可（仕様書 §13）
        if result.dry_run:
            tracker_status = "succeeded"
            result.status = "succeeded"
        elif result.results_stubbed > 0 or result.feedback_resolved_count == 0:
            # 0 件時も period/type/negative の 3 stub は作る想定だが、
            # dry_run 以外で stub 済みなら成功。0 件かつ stub 済みも成功。
            tracker_status = "succeeded"
            result.status = "succeeded"
        else:
            tracker_status = "failed"
            result.status = "failed"
            if "GRS-BAT-001" not in result.error_codes:
                result.error_codes.append("GRS-BAT-001")

        self._repos.record_phase(phase=PHASE_ANALYSIS_COMPLETED, status=tracker_status)
        self._tracker.complete(
            batch_id=BATCH_ID,
            job_run_id=result.job_run_id,
            status=tracker_status,
        )
        result.completed_phases.append("finalize")
        return result
