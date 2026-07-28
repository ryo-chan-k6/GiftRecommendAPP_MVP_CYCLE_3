"""CLI entry for BATCH-017 Import Summary 作成 (scaffold / GHA).

Usage:
  python -m batch.application.import_summary --scaffold-demo
  python -m batch.application.import_summary \\
    --job-run-id <new-uuid> --batch-run-id <existing-run-uuid>  # requires DATABASE_URL

非 demo では ``--job-run-id`` は BATCH-017 自身の新規 UUID（tracker / batch_run_log PK）、
``--batch-run-id`` は集計対象の既存 Run UUID。混同すると PK 衝突する。
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

from batch.application.import_summary.job import ImportSummaryJob
from batch.application.import_summary.models import (
    ApiCallLogRow,
    BatchRunLogRow,
    FeatureEmbeddingProgress,
    ProductDiffRow,
    SkipFailCounts,
    StagingItemRow,
)
from batch.application.import_summary.repositories import ImportSummaryRepositories
from batch.application.job_run import JobRunTracker, create_job_run_tracker
from batch.application.observability import (
    ErrorLogWriter,
    PhaseLogWriter,
    create_batch_observability_writers,
)
from batch.config import load_batch_settings
from batch.infrastructure.db import (
    ScaffoldDbWriter,
    create_db_writer,
    is_live_db_reader,
    resolve_job_db_reader,
)

_DEMO_RUN_ID = "scaffold-import-summary-run"


def build_scaffold_demo_job(
    *,
    job_run_tracker: JobRunTracker | None = None,
    phase_log_writer: PhaseLogWriter | None = None,
    error_log_writer: ErrorLogWriter | None = None,
) -> ImportSummaryJob:
    """Build an in-memory job for local / CI smoke without real secrets / DB."""

    repos = ImportSummaryRepositories(
        db_writer=ScaffoldDbWriter(),
        seed_batch_runs=[BatchRunLogRow(batch_run_id=_DEMO_RUN_ID, status="succeeded")],
        seed_api_calls=[
            ApiCallLogRow(
                batch_run_id=_DEMO_RUN_ID, source_api="item_search", item_count=3
            ),
            ApiCallLogRow(
                batch_run_id=_DEMO_RUN_ID, source_api="item_search", item_count=2
            ),
        ],
        seed_diffs=[
            ProductDiffRow(
                batch_run_id=_DEMO_RUN_ID, source_api="item_search", diff_status="new"
            ),
            ProductDiffRow(
                batch_run_id=_DEMO_RUN_ID, source_api="item_search", diff_status="new"
            ),
            ProductDiffRow(
                batch_run_id=_DEMO_RUN_ID,
                source_api="item_search",
                diff_status="updated",
            ),
            ProductDiffRow(
                batch_run_id=_DEMO_RUN_ID,
                source_api="item_search",
                diff_status="unchanged",
            ),
            ProductDiffRow(
                batch_run_id=_DEMO_RUN_ID,
                source_api="item_search",
                diff_status="unavailable",
            ),
        ],
        seed_staging_items=[
            StagingItemRow(batch_run_id=_DEMO_RUN_ID, source_api="item_search"),
        ],
        seed_skip_fail=SkipFailCounts(skipped_count=1, failed_count=0),
        seed_feature_embedding=FeatureEmbeddingProgress(
            feature_completed=True,
            feature_generated_count=4,
            embedding_completed=True,
            embedding_generated_count=3,
        ),
        seed_default_source_api="item_search",
        phase_log_writer=phase_log_writer,
        error_log_writer=error_log_writer,
    )
    return ImportSummaryJob(repositories=repos, job_run_tracker=job_run_tracker)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-017 Import Summary creation")
    parser.add_argument(
        "--job-run-id",
        default="local-run",
        help=(
            "BATCH-017 自身の job_run_id（tracker / batch_run_log）。"
            "Non --scaffold-demo Postgres tracker requires a UUID。"
        ),
    )
    parser.add_argument("--source-api", default="")
    parser.add_argument(
        "--batch-run-id",
        default="",
        help=(
            "集計対象の既存 batch_run_id（require_batch_run / summary INSERT）。"
            "Postgres 経路では --job-run-id（新規）と分離して渡す。"
        ),
    )
    parser.add_argument(
        "--scaffold-demo",
        action="store_true",
        help="Run in-memory scaffold demo (no real DB).",
    )
    args = parser.parse_args(argv)

    if args.scaffold_demo:
        settings = load_batch_settings()
        source_api = (
            args.source_api.strip()
            or settings.batch_import_summary_source_api
            or "item_search"
        )
        batch_run_id = (
            args.batch_run_id.strip()
            or settings.batch_import_summary_batch_run_id
            or _DEMO_RUN_ID
        )
        tracker = create_job_run_tracker(scaffold_demo=True, database_url=None)
        obs = create_batch_observability_writers(
            scaffold_demo=True, database_url=None
        )
        job = build_scaffold_demo_job(
            job_run_tracker=tracker,
            phase_log_writer=obs.phase_log_writer,
            error_log_writer=obs.error_log_writer,
        )
        # demo: tracker 用 job_run_id と集計用 batch_run_id を分離可能
        demo_job_run_id = (
            args.job_run_id
            if args.job_run_id not in {"local-run", _DEMO_RUN_ID}
            else f"demo-017-{_DEMO_RUN_ID}"
        )
        job.repositories.bind_run(batch_run_id=demo_job_run_id)
        result = job.run(
            job_run_id=demo_job_run_id,
            source_api=source_api,
            batch_run_id=_DEMO_RUN_ID if batch_run_id == _DEMO_RUN_ID else batch_run_id,
            now=datetime.now(UTC),
        )
        print(
            f"BATCH-017 scaffold demo status={result.status} "
            f"source_api={result.source_api} "
            f"insert_applied={result.insert_applied} "
            f"conflict_skipped={result.conflict_skipped} "
            f"phases={','.join(result.completed_phases)}"
        )
        return 0 if result.status in {"succeeded", "partially_succeeded"} else 1

    settings = load_batch_settings()
    db_writer = create_db_writer(settings.database_url)
    tracker = create_job_run_tracker(
        scaffold_demo=False,
        database_url=settings.database_url,
        db_writer=db_writer,
    )
    obs = create_batch_observability_writers(
        scaffold_demo=False,
        database_url=settings.database_url,
        db_writer=db_writer,
    )
    db_reader = resolve_job_db_reader(
        scaffold_demo=False,
        database_url=settings.database_url,
    )
    if not is_live_db_reader(db_reader):
        print(
            "DATABASE_URL is required for non --scaffold-demo BATCH-017 "
            "(DbReader postgres backend). Use --scaffold-demo for local/CI.",
            file=sys.stderr,
        )
        return 2

    source_api = (
        args.source_api.strip()
        or settings.batch_import_summary_source_api
        or "item_search"
    )
    batch_run_id = (
        args.batch_run_id.strip()
        or settings.batch_import_summary_batch_run_id
        or ""
    )
    if not batch_run_id:
        print(
            "BATCH-017 Postgres 経路では --batch-run-id（既存 Run）が必須です。"
            " --job-run-id は BATCH-017 自身の新規 UUID です。",
            file=sys.stderr,
        )
        return 2

    repos = ImportSummaryRepositories(
        db_writer=db_writer,
        db_reader=db_reader,
        seed_default_source_api=source_api,  # type: ignore[arg-type]
        phase_log_writer=obs.phase_log_writer,
        error_log_writer=obs.error_log_writer,
    )
    job = ImportSummaryJob(repositories=repos, job_run_tracker=tracker)
    job.repositories.bind_run(batch_run_id=args.job_run_id)
    result = job.run(
        job_run_id=args.job_run_id,
        source_api=source_api,
        batch_run_id=batch_run_id,
        now=datetime.now(UTC),
    )
    print(
        f"BATCH-017 status={result.status} "
        f"db_reader={db_reader.backend} "
        f"db_writer={db_writer.backend} "
        f"source_api={result.source_api} "
        f"insert_applied={result.insert_applied} "
        f"conflict_skipped={result.conflict_skipped} "
        f"error_codes={','.join(result.error_codes) if result.error_codes else '-'} "
        f"phases={','.join(result.completed_phases)}"
    )
    if result.error_codes:
        for entry in repos.error_logs:
            print(
                f"import_summary.error code={entry.get('code')} "
                f"summary={entry.get('summary')}",
                file=sys.stderr,
            )
    return 0 if result.status in {"succeeded", "partially_succeeded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
