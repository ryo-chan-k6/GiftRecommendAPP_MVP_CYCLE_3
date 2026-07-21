"""BATCH-019 Feedback分析 domain models (in-memory / scaffold).

IF-DB-BATCH-019 = 論理契約。scaffold は in-memory / stub（実 DB INSERT なし）。
feedback_metric は当面 analysis_result_json 内包（§18.1 No.17）。
recommendation_feedback は SELECT のみ（UPDATE / 書戻し禁止）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

FeedbackAnalysisRunStatus = Literal["succeeded", "partially_succeeded", "failed"]
AnalysisType = Literal["negative_trend", "type_breakdown", "period_aggregate"]

# Negative feedback_type（仕様書 §6.2）。packages feedback_type.yaml enabled 値。
NEGATIVE_FEEDBACK_TYPES: frozenset[str] = frozenset(
    {
        "item_bad",
        "item_not_match",
        "item_ng_violation",
        "item_avoid_match",
        "reason_bad",
        "result_bad",
    }
)

# 仮置き閾値（§18.1 No.22）。rating <= 閾値を Negative 扱い。本格化前に Human 確認。
DEFAULT_NEGATIVE_RATING_THRESHOLD = 2

# scaffold 固定 stub（secret ではない）
DEFAULT_AGGREGATION_SCOPE = "manual"


@dataclass(frozen=True)
class RecommendationFeedbackRow:
    """recommendation_feedback 読取行（書込禁止・fixture / SELECT のみ）."""

    recommendation_feedback_id: str
    feedback_type: str
    feedback_target_type: str
    feedback_rating: int
    submitted_at: datetime
    recommendation_result_id: str | None = None
    recommendation_result_item_id: str | None = None
    recommendation_reason_id: str | None = None
    session_id: str | None = None
    # feedback_text は PII 寄りのため集計キーに使わず、fixture でも原則載せない


@dataclass(frozen=True)
class FeedbackAnalysisResultRow:
    """feedback_analysis_result 論理行（IF-DB-BATCH-019 stub）.

    feedback_metric 相当は analysis_result_json['metrics'] に内包する。
    """

    feedback_analysis_result_id: str
    recommendation_feedback_id: str | None
    analysis_type: AnalysisType
    analysis_result_json: dict[str, object]
    analyzed_at: datetime
    batch_run_id: str | None = None
    aggregation_scope: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    semantic_config_version_id: str | None = None


@dataclass
class FeedbackAnalysisJobResult:
    batch_id: str
    job_run_id: str
    status: FeedbackAnalysisRunStatus = "failed"
    completed_phases: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
    feedback_resolved_count: int = 0
    negative_count: int = 0
    results_stubbed: int = 0
    dry_run: bool = False
    period_start: datetime | None = None
    period_end: datetime | None = None
    aggregation_scope: str | None = None
    # 禁止経路カウンタ（常に 0）
    feedback_write_count: int = 0
    feedback_update_count: int = 0
    real_db_insert_count: int = 0
