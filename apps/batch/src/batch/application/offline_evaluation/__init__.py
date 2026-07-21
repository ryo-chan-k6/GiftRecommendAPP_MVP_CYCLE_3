"""BATCH-018 Offline Evaluation application package.

MOD-BATCH-039 Offline Evaluation Runner
MOD-BATCH-040 Evaluation Metric Calculator
MOD-BATCH-041 Evaluation Result Writer
"""

from batch.application.offline_evaluation.job import (
    BATCH_ID,
    OFFLINE_EVALUATION_PHASES,
    PHASE_EVALUATION_COMPLETED,
    OfflineEvaluationError,
    OfflineEvaluationJob,
)
from batch.application.offline_evaluation.metrics import (
    calculate_mvp_metrics,
    extract_relevant_item_ids,
    mrr_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from batch.application.offline_evaluation.models import (
    DEFAULT_MATCHING_CONFIG_ID,
    DEFAULT_MODEL_VERSION_ID,
    DEFAULT_RANKING_CONFIG_ID,
    DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
    METRIC_K,
    MVP_METRIC_NAMES,
    EvaluationCaseRow,
    EvaluationDatasetRow,
    EvaluationMetricRow,
    EvaluationResultRow,
    EvaluationRunRow,
    MetricScore,
    OfflineEvaluationJobResult,
)
from batch.application.offline_evaluation.repositories import (
    DuplicateInsertError,
    OfflineEvaluationRepositories,
)

__all__ = [
    "BATCH_ID",
    "DEFAULT_MATCHING_CONFIG_ID",
    "DEFAULT_MODEL_VERSION_ID",
    "DEFAULT_RANKING_CONFIG_ID",
    "DEFAULT_SEMANTIC_CONFIG_VERSION_ID",
    "METRIC_K",
    "MVP_METRIC_NAMES",
    "OFFLINE_EVALUATION_PHASES",
    "PHASE_EVALUATION_COMPLETED",
    "DuplicateInsertError",
    "EvaluationCaseRow",
    "EvaluationDatasetRow",
    "EvaluationMetricRow",
    "EvaluationResultRow",
    "EvaluationRunRow",
    "MetricScore",
    "OfflineEvaluationError",
    "OfflineEvaluationJob",
    "OfflineEvaluationJobResult",
    "OfflineEvaluationRepositories",
    "calculate_mvp_metrics",
    "extract_relevant_item_ids",
    "mrr_at_k",
    "ndcg_at_k",
    "precision_at_k",
    "recall_at_k",
]
