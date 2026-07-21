"""MOD-BATCH-042 Feedback Analyzer 内部責務.

- Negative Feedback Classifier
- Feedback Metric Aggregator

メトリクスは独立テーブルではなく analysis_result_json 内包（§18.1 No.17）。
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Iterable

from batch.application.feedback_analysis.models import (
    DEFAULT_NEGATIVE_RATING_THRESHOLD,
    NEGATIVE_FEEDBACK_TYPES,
    RecommendationFeedbackRow,
)


def is_negative_feedback(
    row: RecommendationFeedbackRow,
    *,
    rating_threshold: int = DEFAULT_NEGATIVE_RATING_THRESHOLD,
) -> bool:
    """Negative 判定（仕様書 §6.2）。

    - feedback_type が Negative 集合に含まれる
    - または feedback_rating <= rating_threshold（仮置き）
    """

    if row.feedback_type in NEGATIVE_FEEDBACK_TYPES:
        return True
    return row.feedback_rating <= rating_threshold


def classify_feedbacks(
    rows: Iterable[RecommendationFeedbackRow],
    *,
    rating_threshold: int = DEFAULT_NEGATIVE_RATING_THRESHOLD,
) -> tuple[tuple[RecommendationFeedbackRow, ...], tuple[RecommendationFeedbackRow, ...]]:
    """Feedback を Negative / Non-negative に分類する."""

    negatives: list[RecommendationFeedbackRow] = []
    others: list[RecommendationFeedbackRow] = []
    for row in rows:
        if is_negative_feedback(row, rating_threshold=rating_threshold):
            negatives.append(row)
        else:
            others.append(row)
    return tuple(negatives), tuple(others)


def aggregate_metrics(
    rows: Iterable[RecommendationFeedbackRow],
    *,
    negatives: Iterable[RecommendationFeedbackRow],
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    aggregation_scope: str | None = None,
    rating_threshold: int = DEFAULT_NEGATIVE_RATING_THRESHOLD,
) -> dict[str, object]:
    """件数・比率等のメトリクスを JSON 内包用 dict に集計する.

    feedback_metric 独立テーブルは作らない（案 B）。
    """

    rows_list = list(rows)
    negatives_list = list(negatives)
    total = len(rows_list)
    negative_count = len(negatives_list)
    type_counts = Counter(row.feedback_type for row in rows_list)
    target_counts = Counter(row.feedback_target_type for row in rows_list)
    rating_hist = Counter(row.feedback_rating for row in rows_list)

    return {
        "aggregation_scope": aggregation_scope,
        "period_start": period_start.isoformat() if period_start else None,
        "period_end": period_end.isoformat() if period_end else None,
        "total_count": total,
        "negative_count": negative_count,
        "negative_ratio": (negative_count / float(total)) if total > 0 else 0.0,
        "negative_rating_threshold": rating_threshold,
        "by_feedback_type": dict(sorted(type_counts.items())),
        "by_feedback_target_type": dict(sorted(target_counts.items())),
        "rating_histogram": {
            str(k): v for k, v in sorted(rating_hist.items())
        },
    }


def build_period_aggregate_payload(
    *,
    metrics: dict[str, object],
    job_run_id: str,
) -> dict[str, object]:
    """analysis_type=period_aggregate 用の analysis_result_json."""

    return {
        "summary": "period_aggregate",
        "batch_run_id": job_run_id,
        "metrics": metrics,
    }


def build_type_breakdown_payload(
    *,
    metrics: dict[str, object],
    job_run_id: str,
) -> dict[str, object]:
    return {
        "summary": "type_breakdown",
        "batch_run_id": job_run_id,
        "metrics": {
            "by_feedback_type": metrics.get("by_feedback_type", {}),
            "total_count": metrics.get("total_count", 0),
        },
    }


def build_negative_trend_payload(
    *,
    metrics: dict[str, object],
    job_run_id: str,
) -> dict[str, object]:
    return {
        "summary": "negative_trend",
        "batch_run_id": job_run_id,
        "metrics": {
            "total_count": metrics.get("total_count", 0),
            "negative_count": metrics.get("negative_count", 0),
            "negative_ratio": metrics.get("negative_ratio", 0.0),
            "negative_rating_threshold": metrics.get("negative_rating_threshold"),
            "by_feedback_target_type": metrics.get("by_feedback_target_type", {}),
        },
    }
