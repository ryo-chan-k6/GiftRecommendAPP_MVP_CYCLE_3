"""BATCH-018 Offline Evaluation ジョブ実装.

Phases（仕様書 §8.2）:
open_run → resolve_dataset → insert_run → start_run → evaluate_cases →
write_metrics → finalize

モジュール:
- MOD-BATCH-039 Offline Evaluation Runner（本ジョブ）
- MOD-BATCH-040 Evaluation Metric Calculator（metrics.py）
- MOD-BATCH-041 Evaluation Result Writer（repositories.insert_result）

物理書込 IF = IF-DB-BATCH-018 のみ。
推薦実行 IF = IF-SHARED-004（scaffold: mock）。
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from batch.application.job_run import JobRunTracker, ScaffoldJobRunTracker
from batch.application.offline_evaluation.metrics import calculate_mvp_metrics
from batch.application.offline_evaluation.models import (
    DEFAULT_MATCHING_CONFIG_ID,
    DEFAULT_MODEL_VERSION_ID,
    DEFAULT_RANKING_CONFIG_ID,
    DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
    EvaluationResultRow,
    EvaluationRunRow,
    OfflineEvaluationJobResult,
)
from batch.application.offline_evaluation.repositories import (
    DuplicateInsertError,
    OfflineEvaluationRepositories,
)
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger
from batch.infrastructure.reco_client import (
    MockRecoEvaluationClient,
    RecoEvaluationClient,
    RecoEvaluationRequest,
)

BATCH_ID = "BATCH-018"
OFFLINE_EVALUATION_PHASES: tuple[str, ...] = (
    "open_run",
    "resolve_dataset",
    "insert_run",
    "start_run",
    "evaluate_cases",
    "write_metrics",
    "finalize",
)
PHASE_EVALUATION_COMPLETED = "evaluation_completed"


class OfflineEvaluationError(Exception):
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


class OfflineEvaluationJob:
    """MOD-BATCH-039 Offline Evaluation Runner オーケストレータ."""

    def __init__(
        self,
        *,
        repositories: OfflineEvaluationRepositories,
        reco_client: RecoEvaluationClient | None = None,
        job_run_tracker: JobRunTracker | None = None,
        logger: BatchLogger | None = None,
    ) -> None:
        self._repos = repositories
        self._reco = reco_client or MockRecoEvaluationClient()
        self._tracker = job_run_tracker or ScaffoldJobRunTracker()
        self._logger = logger or ScaffoldBatchLogger()

    def run(
        self,
        *,
        job_run_id: str,
        evaluation_dataset_id: str | None = None,
        dataset_name: str | None = None,
        dataset_version: str | None = None,
        max_cases: int | None = None,
        dry_run: bool = False,
        semantic_config_version_id: str | None = None,
        model_version_id: str | None = None,
        matching_config_id: str | None = None,
        ranking_config_id: str | None = None,
        trace_id: str | None = None,
        now: datetime | None = None,
    ) -> OfflineEvaluationJobResult:
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        _ = bound_logger
        ts = now or datetime.now(UTC)
        result = OfflineEvaluationJobResult(
            batch_id=BATCH_ID,
            job_run_id=job_run_id,
            status="failed",
            dry_run=dry_run,
        )

        if _is_batch_already_running(self._tracker):
            result.error_codes.append("GRS-BAT-003")
            self._repos.record_error(code="GRS-BAT-003", summary="batch already running")
            return result

        self._tracker.start(batch_id=BATCH_ID, job_run_id=job_run_id)
        result.completed_phases.append("open_run")

        try:
            try:
                dataset = self._repos.resolve_dataset(
                    evaluation_dataset_id=evaluation_dataset_id,
                    dataset_name=dataset_name,
                    dataset_version=dataset_version,
                )
            except LookupError as exc:
                raise OfflineEvaluationError("GRS-CFG-001", str(exc)) from exc

            cases = self._repos.load_active_cases(
                evaluation_dataset_id=dataset.evaluation_dataset_id,
                max_cases=max_cases,
            )
            if not cases:
                raise OfflineEvaluationError(
                    "GRS-VAL-001",
                    f"no active evaluation_case for dataset={dataset.evaluation_dataset_id}",
                )

            result.evaluation_dataset_id = dataset.evaluation_dataset_id
            result.completed_phases.append("resolve_dataset")
            self._repos.record_phase(phase="dataset_resolved", status="succeeded")

            run_id = str(uuid4())
            run_row = EvaluationRunRow(
                evaluation_run_id=run_id,
                evaluation_dataset_id=dataset.evaluation_dataset_id,
                semantic_config_version_id=(
                    (semantic_config_version_id or "").strip()
                    or DEFAULT_SEMANTIC_CONFIG_VERSION_ID
                ),
                model_version_id=(
                    (model_version_id or "").strip() or DEFAULT_MODEL_VERSION_ID
                ),
                matching_config_id=(
                    (matching_config_id or "").strip() or DEFAULT_MATCHING_CONFIG_ID
                ),
                ranking_config_id=(
                    (ranking_config_id or "").strip() or DEFAULT_RANKING_CONFIG_ID
                ),
                evaluation_status="queued",
                batch_run_id=job_run_id,
            )
            if not dry_run:
                self._repos.insert_run(run_row)
            result.evaluation_run_id = run_id
            result.evaluation_status = "queued"
            result.completed_phases.append("insert_run")

            if not dry_run:
                self._repos.update_run_status(
                    evaluation_run_id=run_id,
                    evaluation_status="running",
                    started_at=ts,
                )
            result.evaluation_status = "running"
            result.completed_phases.append("start_run")
            self._repos.record_phase(phase="evaluation_started", status="running")

            metrics_written = 0
            results_written = 0
            case_failures = 0

            for case in cases:
                reco = self._reco.evaluate(
                    RecoEvaluationRequest(
                        evaluation_case_id=case.evaluation_case_id,
                        evaluation_run_id=run_id,
                        input_condition_json=case.input_condition_json,
                        expected_result_json=case.expected_result_json,
                        mode="evaluation",
                    )
                )
                result_id = str(uuid4())
                recommendation_result_id = (
                    reco.recommendation_result_id if reco.ok else None
                )
                if not reco.ok:
                    case_failures += 1
                    self._repos.record_error(
                        code=reco.error_code or "GRS-REC-000",
                        summary=reco.error_summary or "reco evaluation failed",
                    )

                result_row = EvaluationResultRow(
                    evaluation_result_id=result_id,
                    evaluation_run_id=run_id,
                    evaluation_case_id=case.evaluation_case_id,
                    evaluation_dataset_id=dataset.evaluation_dataset_id,
                    recommendation_result_id=recommendation_result_id,
                )
                if not dry_run:
                    try:
                        self._repos.insert_result(result_row)
                        results_written += 1
                    except DuplicateInsertError as exc:
                        raise OfflineEvaluationError("GRS-VAL-002", str(exc)) from exc

                try:
                    scores = calculate_mvp_metrics(
                        predicted_item_ids=reco.predicted_item_ids if reco.ok else (),
                        expected_result_json=case.expected_result_json,
                    )
                except ValueError as exc:
                    self._repos.record_error(code="GRS-EVAL-004", summary=str(exc))
                    scores = ()

                if scores and not dry_run:
                    try:
                        inserted = self._repos.insert_metrics(
                            evaluation_result_id=result_id, scores=scores
                        )
                        metrics_written += len(inserted)
                    except DuplicateInsertError as exc:
                        raise OfflineEvaluationError("GRS-VAL-002", str(exc)) from exc
                elif case.expected_result_json is None:
                    self._repos.record_error(
                        code="GRS-EVAL-003",
                        summary=(
                            f"expected_result_json missing; metrics skipped "
                            f"case={case.evaluation_case_id}"
                        ),
                    )

            result.cases_evaluated = len(cases)
            result.results_inserted = results_written
            result.metrics_inserted = metrics_written
            result.completed_phases.append("evaluate_cases")
            result.completed_phases.append("write_metrics")
            self._repos.record_phase(phase="case_evaluated", status="succeeded")
            self._repos.record_phase(phase="metrics_written", status="succeeded")

            result.dataset_write_count = self._repos.dataset_write_count
            result.case_write_count = self._repos.case_write_count
            result.result_update_count = self._repos.result_update_count
            result.metric_update_count = self._repos.metric_update_count
            # mock は HTTP を使わない
            result.http_call_count = 0

            return self._phase_finalize(
                result,
                run_id=run_id,
                case_failures=case_failures,
                dry_run=dry_run,
                now=ts,
            )
        except OfflineEvaluationError as exc:
            result.error_codes.append(exc.code)
            self._repos.record_error(code=exc.code, summary=exc.message)
            if result.evaluation_run_id and not dry_run:
                try:
                    self._repos.update_run_status(
                        evaluation_run_id=result.evaluation_run_id,
                        evaluation_status="failed",
                        completed_at=ts,
                    )
                    result.evaluation_status = "failed"
                except LookupError:
                    pass
            self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
            result.completed_phases.append("finalize")
            result.status = "failed"
            return result
        except Exception:
            self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
            raise

    def _phase_finalize(
        self,
        result: OfflineEvaluationJobResult,
        *,
        run_id: str,
        case_failures: int,
        dry_run: bool,
        now: datetime,
    ) -> OfflineEvaluationJobResult:
        if case_failures == 0 and result.results_inserted > 0:
            eval_status = "succeeded"
            tracker_status = "succeeded"
            result.status = "succeeded"
        elif result.results_inserted > 0:
            eval_status = "succeeded"
            tracker_status = "partially_succeeded"
            result.status = "partially_succeeded"
            if "GRS-BAT-002" not in result.error_codes:
                result.error_codes.append("GRS-BAT-002")
        elif dry_run and result.cases_evaluated > 0:
            eval_status = "succeeded"
            tracker_status = "succeeded"
            result.status = "succeeded"
        else:
            eval_status = "failed"
            tracker_status = "failed"
            result.status = "failed"
            if "GRS-BAT-001" not in result.error_codes:
                result.error_codes.append("GRS-BAT-001")

        if not dry_run:
            self._repos.update_run_status(
                evaluation_run_id=run_id,
                evaluation_status=eval_status,  # type: ignore[arg-type]
                completed_at=now,
            )
        result.evaluation_status = eval_status  # type: ignore[assignment]

        self._repos.record_phase(
            phase=PHASE_EVALUATION_COMPLETED, status=tracker_status
        )
        self._tracker.complete(
            batch_id=BATCH_ID,
            job_run_id=result.job_run_id,
            status=tracker_status,
        )
        result.completed_phases.append("finalize")
        return result
