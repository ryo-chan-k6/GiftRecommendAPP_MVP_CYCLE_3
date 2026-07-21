"""In-memory repositories for BATCH-018 scaffold / UT.

- evaluation_dataset / evaluation_case READ ONLY（本番 seed は別 Task）
- IF-DB-BATCH-018: evaluation_run INSERT + 状態 UPDATE /
  evaluation_result INSERT のみ / evaluation_metric INSERT のみ
- Result / Metric の UPDATE 経路なし
- evaluation_run_log テーブルは参照・作成しない
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from batch.application.offline_evaluation.models import (
    EvaluationCaseRow,
    EvaluationDatasetRow,
    EvaluationMetricRow,
    EvaluationResultRow,
    EvaluationRunRow,
    EvaluationStatus,
    MetricScore,
)
from batch.infrastructure.db import DbWriter


class DuplicateInsertError(LookupError):
    """UNIQUE 制約相当（INSERT のみ・UPDATE なし）。"""


@dataclass
class OfflineEvaluationRepositories:
    """Facade: Dataset/Case 読取 / IF-DB-BATCH-018 書込 / phase・error logs."""

    db_writer: DbWriter
    seed_datasets: list[EvaluationDatasetRow] = field(default_factory=list)
    seed_cases: list[EvaluationCaseRow] = field(default_factory=list)

    datasets: list[EvaluationDatasetRow] = field(default_factory=list)
    cases: list[EvaluationCaseRow] = field(default_factory=list)

    runs: list[EvaluationRunRow] = field(default_factory=list)
    results: list[EvaluationResultRow] = field(default_factory=list)
    metrics: list[EvaluationMetricRow] = field(default_factory=list)

    run_insert_count: int = 0
    run_status_update_count: int = 0
    result_insert_count: int = 0
    metric_insert_count: int = 0

    # 禁止経路カウンタ（常に 0 を維持）
    dataset_write_count: int = 0
    case_write_count: int = 0
    result_update_count: int = 0
    metric_update_count: int = 0
    evaluation_run_log_write_count: int = 0

    phase_logs: list[dict[str, object]] = field(default_factory=list)
    error_logs: list[dict[str, object]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.datasets = list(self.seed_datasets)
        self.cases = list(self.seed_cases)

    def resolve_dataset(
        self,
        *,
        evaluation_dataset_id: str | None = None,
        dataset_name: str | None = None,
        dataset_version: str | None = None,
    ) -> EvaluationDatasetRow:
        if evaluation_dataset_id:
            for row in self.datasets:
                if row.evaluation_dataset_id == evaluation_dataset_id:
                    if not row.is_active:
                        raise LookupError(
                            f"evaluation_dataset inactive: {evaluation_dataset_id}"
                        )
                    return row
            raise LookupError(f"evaluation_dataset not found: {evaluation_dataset_id}")

        name = (dataset_name or "").strip()
        version = (dataset_version or "").strip()
        if not name or not version:
            raise LookupError(
                "evaluation_dataset_id or (dataset_name + dataset_version) required"
            )
        for row in self.datasets:
            if (
                row.dataset_name == name
                and row.dataset_version == version
                and row.is_active
            ):
                return row
        raise LookupError(f"evaluation_dataset not found: {name}@{version}")

    def load_active_cases(
        self, *, evaluation_dataset_id: str, max_cases: int | None = None
    ) -> tuple[EvaluationCaseRow, ...]:
        rows = [
            row
            for row in self.cases
            if row.evaluation_dataset_id == evaluation_dataset_id and row.is_active
        ]
        if max_cases is not None and max_cases > 0:
            rows = rows[:max_cases]
        return tuple(rows)

    def insert_run(self, row: EvaluationRunRow) -> EvaluationRunRow:
        """IF-DB-BATCH-018: evaluation_run INSERT（毎回新規・自然キー UNIQUE なし）."""

        self.run_insert_count += 1
        self.runs.append(row)
        self.db_writer.write_rows(
            "evaluation_run",
            (self._run_payload(row, op="if_db_batch_018_insert"),),
        )
        return row

    def update_run_status(
        self,
        *,
        evaluation_run_id: str,
        evaluation_status: EvaluationStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> EvaluationRunRow:
        """Run 状態遷移 UPDATE のみ（Result/Metric 上書きではない）."""

        for index, row in enumerate(self.runs):
            if row.evaluation_run_id != evaluation_run_id:
                continue
            updated = EvaluationRunRow(
                evaluation_run_id=row.evaluation_run_id,
                evaluation_dataset_id=row.evaluation_dataset_id,
                semantic_config_version_id=row.semantic_config_version_id,
                model_version_id=row.model_version_id,
                matching_config_id=row.matching_config_id,
                ranking_config_id=row.ranking_config_id,
                evaluation_status=evaluation_status,
                batch_run_id=row.batch_run_id,
                started_at=started_at if started_at is not None else row.started_at,
                completed_at=(
                    completed_at if completed_at is not None else row.completed_at
                ),
            )
            self.runs[index] = updated
            self.run_status_update_count += 1
            self.db_writer.write_rows(
                "evaluation_run",
                (self._run_payload(updated, op="if_db_batch_018_status_update"),),
            )
            return updated
        raise LookupError(f"evaluation_run not found: {evaluation_run_id}")

    def insert_result(self, row: EvaluationResultRow) -> EvaluationResultRow:
        """IF-DB-BATCH-018: evaluation_result INSERT のみ（UPDATE なし）."""

        key = (row.evaluation_run_id, row.evaluation_case_id)
        existing = {
            (r.evaluation_run_id, r.evaluation_case_id) for r in self.results
        }
        if key in existing:
            raise DuplicateInsertError(
                f"evaluation_result unique violation: run={row.evaluation_run_id} "
                f"case={row.evaluation_case_id}"
            )
        self.results.append(row)
        self.result_insert_count += 1
        self.db_writer.write_rows(
            "evaluation_result",
            (self._result_payload(row),),
        )
        return row

    def insert_metrics(
        self, *, evaluation_result_id: str, scores: tuple[MetricScore, ...]
    ) -> tuple[EvaluationMetricRow, ...]:
        """IF-DB-BATCH-018: evaluation_metric INSERT のみ（UPDATE なし）."""

        inserted: list[EvaluationMetricRow] = []
        existing_names = {
            m.metric_name
            for m in self.metrics
            if m.evaluation_result_id == evaluation_result_id
        }
        for score in scores:
            if score.metric_name in existing_names:
                raise DuplicateInsertError(
                    f"evaluation_metric unique violation: result={evaluation_result_id} "
                    f"name={score.metric_name}"
                )
            row = EvaluationMetricRow(
                evaluation_metric_id=str(uuid4()),
                evaluation_result_id=evaluation_result_id,
                metric_name=score.metric_name,
                metric_value=score.metric_value,
                metric_detail_json=score.metric_detail_json,
            )
            self.metrics.append(row)
            self.metric_insert_count += 1
            existing_names.add(score.metric_name)
            inserted.append(row)
            self.db_writer.write_rows(
                "evaluation_metric",
                (self._metric_payload(row),),
            )
        return tuple(inserted)

    def record_phase(
        self, *, phase: str, status: str, owner_type: str = "evaluation_run"
    ) -> None:
        self.phase_logs.append(
            {"phase": phase, "status": status, "owner_type": owner_type}
        )

    def record_error(
        self, *, code: str, summary: str, owner_type: str = "evaluation_run"
    ) -> None:
        self.error_logs.append(
            {"code": code, "summary": summary, "owner_type": owner_type}
        )

    @staticmethod
    def _run_payload(row: EvaluationRunRow, *, op: str) -> dict[str, object]:
        return {
            "evaluation_run_id": row.evaluation_run_id,
            "evaluation_dataset_id": row.evaluation_dataset_id,
            "semantic_config_version_id": row.semantic_config_version_id,
            "model_version_id": row.model_version_id,
            "matching_config_id": row.matching_config_id,
            "ranking_config_id": row.ranking_config_id,
            "evaluation_status": row.evaluation_status,
            "batch_run_id": row.batch_run_id,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            "op": op,
        }

    @staticmethod
    def _result_payload(row: EvaluationResultRow) -> dict[str, object]:
        return {
            "evaluation_result_id": row.evaluation_result_id,
            "evaluation_run_id": row.evaluation_run_id,
            "evaluation_case_id": row.evaluation_case_id,
            "evaluation_dataset_id": row.evaluation_dataset_id,
            "recommendation_result_id": row.recommendation_result_id,
            "op": "if_db_batch_018_insert",
        }

    @staticmethod
    def _metric_payload(row: EvaluationMetricRow) -> dict[str, object]:
        return {
            "evaluation_metric_id": row.evaluation_metric_id,
            "evaluation_result_id": row.evaluation_result_id,
            "metric_name": row.metric_name,
            "metric_value": row.metric_value,
            "metric_detail_json": row.metric_detail_json,
            "op": "if_db_batch_018_insert",
        }
