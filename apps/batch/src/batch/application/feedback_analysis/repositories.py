"""In-memory repositories for BATCH-019 scaffold / UT.

- recommendation_feedback READ ONLY（SELECT / fixture。UPDATE・書戻し禁止）
- IF-DB-BATCH-019: feedback_analysis_result stub（都度新規・実 DB INSERT なし）
- feedback_metric 独立テーブルなし（JSON 内包）
- MOD-BATCH-043 / 044 経路なし
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from batch.application.feedback_analysis.models import (
    FeedbackAnalysisResultRow,
    RecommendationFeedbackRow,
)
from batch.infrastructure.db import DbWriter


@dataclass
class FeedbackAnalysisRepositories:
    """Facade: Feedback 読取 / IF-DB-BATCH-019 stub / phase・error logs."""

    db_writer: DbWriter
    seed_feedbacks: list[RecommendationFeedbackRow] = field(default_factory=list)

    feedbacks: list[RecommendationFeedbackRow] = field(default_factory=list)
    analysis_results: list[FeedbackAnalysisResultRow] = field(default_factory=list)

    stub_persist_count: int = 0
    # 禁止経路カウンタ（常に 0 を維持）
    feedback_write_count: int = 0
    feedback_update_count: int = 0
    real_db_insert_count: int = 0
    feedback_metric_table_write_count: int = 0

    phase_logs: list[dict[str, object]] = field(default_factory=list)
    error_logs: list[dict[str, object]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.feedbacks = list(self.seed_feedbacks)

    def load_feedbacks(
        self,
        *,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        feedback_types: frozenset[str] | None = None,
        max_feedback_rows: int | None = None,
    ) -> tuple[RecommendationFeedbackRow, ...]:
        """recommendation_feedback SELECT 相当（fixture フィルタ）."""

        rows: list[RecommendationFeedbackRow] = []
        for row in self.feedbacks:
            if period_start is not None and row.submitted_at < period_start:
                continue
            if period_end is not None and row.submitted_at > period_end:
                continue
            if feedback_types is not None and row.feedback_type not in feedback_types:
                continue
            rows.append(row)
        if max_feedback_rows is not None and max_feedback_rows > 0:
            rows = rows[:max_feedback_rows]
        return tuple(rows)

    def stub_persist_analysis_results(
        self, rows: tuple[FeedbackAnalysisResultRow, ...]
    ) -> tuple[FeedbackAnalysisResultRow, ...]:
        """IF-DB-BATCH-019 stub: 実行都度新規オブジェクトを保持（実 INSERT なし）.

        ScaffoldDbWriter へは stub マーカー付きで記録するのみ。
        物理テーブル DDL / migration は対象外。
        """

        persisted: list[FeedbackAnalysisResultRow] = []
        for row in rows:
            self.analysis_results.append(row)
            self.stub_persist_count += 1
            persisted.append(row)
            self.db_writer.write_rows(
                "feedback_analysis_result_stub",
                (self._stub_payload(row),),
            )
        return tuple(persisted)

    def record_phase(
        self, *, phase: str, status: str, owner_type: str = "batch_run"
    ) -> None:
        """feedback_analysis_status 読み替え先（phase_log）。owner_type=batch_run."""

        self.phase_logs.append(
            {"phase": phase, "status": status, "owner_type": owner_type}
        )

    def record_error(
        self, *, code: str, summary: str, owner_type: str = "batch_run"
    ) -> None:
        self.error_logs.append(
            {"code": code, "summary": summary, "owner_type": owner_type}
        )

    @staticmethod
    def _stub_payload(row: FeedbackAnalysisResultRow) -> dict[str, object]:
        return {
            "feedback_analysis_result_id": row.feedback_analysis_result_id,
            "recommendation_feedback_id": row.recommendation_feedback_id,
            "analysis_type": row.analysis_type,
            "analysis_result_json": row.analysis_result_json,
            "analyzed_at": row.analyzed_at.isoformat(),
            "batch_run_id": row.batch_run_id,
            "aggregation_scope": row.aggregation_scope,
            "period_start": row.period_start.isoformat() if row.period_start else None,
            "period_end": row.period_end.isoformat() if row.period_end else None,
            "semantic_config_version_id": row.semantic_config_version_id,
            "op": "if_db_batch_019_stub",
            # metrics は JSON 内包。独立 feedback_metric テーブルへの書込なし
            "feedback_metric_table": None,
        }
