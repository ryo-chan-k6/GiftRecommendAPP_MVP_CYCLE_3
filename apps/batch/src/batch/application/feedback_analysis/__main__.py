"""CLI entry for BATCH-019 Feedback分析 (scaffold / GHA).

Usage:
  python -m batch.application.feedback_analysis --scaffold-demo
  python -m batch.application.feedback_analysis --job-run-id <id>  # exit 3 (real DB off)
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta

from batch.application.feedback_analysis.job import FeedbackAnalysisJob
from batch.application.feedback_analysis.models import RecommendationFeedbackRow
from batch.application.feedback_analysis.repositories import (
    FeedbackAnalysisRepositories,
)
from batch.config import load_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter

_DEMO_NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=UTC)


def build_scaffold_demo_job() -> FeedbackAnalysisJob:
    """Build an in-memory job for local / CI smoke without real secrets / DB."""

    feedbacks = [
        RecommendationFeedbackRow(
            recommendation_feedback_id="fb-scaffold-001",
            feedback_type="item_bad",
            feedback_target_type="item",
            feedback_rating=2,
            submitted_at=_DEMO_NOW - timedelta(days=1),
            recommendation_result_id="rr-1",
            recommendation_result_item_id="rri-1",
        ),
        RecommendationFeedbackRow(
            recommendation_feedback_id="fb-scaffold-002",
            feedback_type="item_good",
            feedback_target_type="item",
            feedback_rating=5,
            submitted_at=_DEMO_NOW - timedelta(hours=12),
            recommendation_result_id="rr-1",
            recommendation_result_item_id="rri-2",
        ),
        RecommendationFeedbackRow(
            recommendation_feedback_id="fb-scaffold-003",
            feedback_type="reason_bad",
            feedback_target_type="reason",
            feedback_rating=1,
            submitted_at=_DEMO_NOW - timedelta(hours=6),
            recommendation_result_id="rr-2",
            recommendation_reason_id="reason-1",
        ),
        RecommendationFeedbackRow(
            recommendation_feedback_id="fb-scaffold-004",
            feedback_type="result_good",
            feedback_target_type="result",
            feedback_rating=4,
            submitted_at=_DEMO_NOW - timedelta(hours=3),
            recommendation_result_id="rr-2",
        ),
    ]
    repos = FeedbackAnalysisRepositories(
        db_writer=ScaffoldDbWriter(),
        seed_feedbacks=feedbacks,
    )
    return FeedbackAnalysisJob(repositories=repos)


def _parse_optional_int(raw: str | None) -> int | None:
    if raw is None or raw.strip() == "":
        return None
    try:
        value = int(raw.strip())
    except ValueError as exc:
        raise SystemExit(f"invalid integer: {raw!r}") from exc
    if value <= 0:
        raise SystemExit(f"must be positive: {raw!r}")
    return value


def _parse_bool(raw: str | None, *, default: bool = False) -> bool:
    if raw is None or raw.strip() == "":
        return default
    lowered = raw.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise SystemExit(f"invalid boolean value: {raw!r}")


def _parse_optional_datetime(raw: str | None) -> datetime | None:
    if raw is None or raw.strip() == "":
        return None
    text = raw.strip()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        value = datetime.fromisoformat(text)
    except ValueError as exc:
        raise SystemExit(f"invalid datetime: {raw!r}") from exc
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-019 Feedback Analysis")
    parser.add_argument("--job-run-id", default="local-run")
    parser.add_argument("--period-start", default="")
    parser.add_argument("--period-end", default="")
    parser.add_argument("--aggregation-scope", default="")
    parser.add_argument("--feedback-types", default="")
    parser.add_argument("--semantic-config-version-id", default="")
    parser.add_argument("--max-feedback-rows", default="")
    parser.add_argument("--dry-run", default="")
    parser.add_argument(
        "--scaffold-demo",
        action="store_true",
        help="Run in-memory scaffold demo (no real DB).",
    )
    args = parser.parse_args(argv)

    if args.scaffold_demo:
        settings = load_batch_settings()
        period_start = _parse_optional_datetime(
            args.period_start or None
        ) or _parse_optional_datetime(settings.batch_feedback_analysis_period_start)
        period_end = _parse_optional_datetime(
            args.period_end or None
        ) or _parse_optional_datetime(settings.batch_feedback_analysis_period_end)
        aggregation_scope = (
            args.aggregation_scope.strip()
            or settings.batch_feedback_analysis_aggregation_scope
            or None
        )
        feedback_types = (
            args.feedback_types.strip()
            or settings.batch_feedback_analysis_feedback_types
            or None
        )
        semantic_config_version_id = (
            args.semantic_config_version_id.strip()
            or settings.batch_feedback_analysis_semantic_config_version_id
            or None
        )
        max_feedback_rows = _parse_optional_int(
            args.max_feedback_rows or None
        ) or settings.batch_feedback_analysis_max_feedback_rows
        dry_run = _parse_bool(
            args.dry_run or None,
            default=bool(settings.batch_feedback_analysis_dry_run),
        )
        negative_rating_threshold = (
            settings.batch_feedback_analysis_negative_rating_threshold or 2
        )
        job = build_scaffold_demo_job()
        result = job.run(
            job_run_id=args.job_run_id,
            period_start=period_start,
            period_end=period_end,
            aggregation_scope=aggregation_scope,
            feedback_types=feedback_types,
            semantic_config_version_id=semantic_config_version_id,
            max_feedback_rows=max_feedback_rows,
            dry_run=dry_run,
            negative_rating_threshold=negative_rating_threshold,
            now=datetime.now(UTC),
        )
        print(
            f"BATCH-019 scaffold demo status={result.status} "
            f"feedbacks={result.feedback_resolved_count} "
            f"negatives={result.negative_count} "
            f"stubbed={result.results_stubbed} "
            f"phases={','.join(result.completed_phases)}"
        )
        return 0 if result.status in {"succeeded", "partially_succeeded"} else 1

    settings = load_batch_settings()
    _ = settings
    print(
        "Real DB client is not enabled in this Task. Use --scaffold-demo for local/CI.",
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
