"""BATCH-018 Offline Evaluation domain models (in-memory / scaffold).

物理書込 IF = IF-DB-BATCH-018（evaluation_run / result / metric INSERT）。
Result / Metric は UPDATE しない。Run 状態遷移 UPDATE のみ許可。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

EvaluationStatus = Literal["queued", "running", "succeeded", "failed", "canceled"]
OfflineEvaluationRunStatus = Literal["succeeded", "partially_succeeded", "failed"]

MVP_METRIC_NAMES: tuple[str, ...] = (
    "precision_at_10",
    "recall_at_10",
    "ndcg_at_10",
    "mrr_at_10",
)

# scaffold 固定 stub UUID（§18.1 No.20）。secret ではない。
DEFAULT_SEMANTIC_CONFIG_VERSION_ID = "01800000-scaf-7000-8000-sem000000001"
DEFAULT_MODEL_VERSION_ID = "01800000-scaf-7000-8000-mod000000001"
DEFAULT_MATCHING_CONFIG_ID = "01800000-scaf-7000-8000-mat000000001"
DEFAULT_RANKING_CONFIG_ID = "01800000-scaf-7000-8000-rnk000000001"

METRIC_K = 10


@dataclass(frozen=True)
class EvaluationDatasetRow:
    """evaluation_dataset 読取行（書込禁止・seed は別 Task）。"""

    evaluation_dataset_id: str
    dataset_name: str
    dataset_version: str
    is_active: bool = True


@dataclass(frozen=True)
class EvaluationCaseRow:
    """evaluation_case 読取行（書込禁止）。"""

    evaluation_case_id: str
    evaluation_dataset_id: str
    case_label: str
    input_condition_json: dict[str, object] | None = None
    expected_result_json: dict[str, object] | None = None
    is_active: bool = True


@dataclass(frozen=True)
class EvaluationRunRow:
    """evaluation_run INSERT / 状態行（IF-DB-BATCH-018）。"""

    evaluation_run_id: str
    evaluation_dataset_id: str
    semantic_config_version_id: str
    model_version_id: str
    matching_config_id: str
    ranking_config_id: str
    evaluation_status: EvaluationStatus
    batch_run_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True)
class EvaluationResultRow:
    """evaluation_result INSERT 行（IF-DB-BATCH-018）。UPDATE 禁止。"""

    evaluation_result_id: str
    evaluation_run_id: str
    evaluation_case_id: str
    evaluation_dataset_id: str
    recommendation_result_id: str | None = None


@dataclass(frozen=True)
class EvaluationMetricRow:
    """evaluation_metric INSERT 行（IF-DB-BATCH-018）。UPDATE 禁止。"""

    evaluation_metric_id: str
    evaluation_result_id: str
    metric_name: str
    metric_value: float
    metric_detail_json: dict[str, object] | None = None


@dataclass(frozen=True)
class MetricScore:
    """MOD-BATCH-040 算出結果 1 指標。"""

    metric_name: str
    metric_value: float
    metric_detail_json: dict[str, object] | None = None


@dataclass
class OfflineEvaluationJobResult:
    batch_id: str
    job_run_id: str
    status: OfflineEvaluationRunStatus = "failed"
    completed_phases: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
    evaluation_dataset_id: str | None = None
    evaluation_run_id: str | None = None
    evaluation_status: EvaluationStatus | None = None
    cases_evaluated: int = 0
    results_inserted: int = 0
    metrics_inserted: int = 0
    dry_run: bool = False
    # 隣接 / 禁止書込カウンタ（常に 0）
    dataset_write_count: int = 0
    case_write_count: int = 0
    result_update_count: int = 0
    metric_update_count: int = 0
    http_call_count: int = 0
