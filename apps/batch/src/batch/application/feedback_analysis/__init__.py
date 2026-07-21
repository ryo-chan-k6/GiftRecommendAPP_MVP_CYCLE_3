"""BATCH-019 Feedback分析 application package.

MOD-BATCH-042 Feedback Analyzer
（Aggregator / Classifier は内部責務。MOD-BATCH-043 / 044 は out of scope）
"""

from batch.application.feedback_analysis.analyzer import (
    aggregate_metrics,
    build_negative_trend_payload,
    build_period_aggregate_payload,
    build_type_breakdown_payload,
    classify_feedbacks,
    is_negative_feedback,
)
from batch.application.feedback_analysis.job import (
    BATCH_ID,
    FEEDBACK_ANALYSIS_PHASES,
    PHASE_ANALYSIS_COMPLETED,
    FeedbackAnalysisError,
    FeedbackAnalysisJob,
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

__all__ = [
    "BATCH_ID",
    "DEFAULT_AGGREGATION_SCOPE",
    "DEFAULT_NEGATIVE_RATING_THRESHOLD",
    "FEEDBACK_ANALYSIS_PHASES",
    "NEGATIVE_FEEDBACK_TYPES",
    "PHASE_ANALYSIS_COMPLETED",
    "FeedbackAnalysisError",
    "FeedbackAnalysisJob",
    "FeedbackAnalysisJobResult",
    "FeedbackAnalysisRepositories",
    "FeedbackAnalysisResultRow",
    "RecommendationFeedbackRow",
    "aggregate_metrics",
    "build_negative_trend_payload",
    "build_period_aggregate_payload",
    "build_type_breakdown_payload",
    "classify_feedbacks",
    "is_negative_feedback",
]
