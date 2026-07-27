"""CLI entry for BATCH-017 Import Summary 作成 (scaffold / GHA).

Usage:
  python -m batch.application.import_summary --scaffold-demo
  python -m batch.application.import_summary --job-run-id <id>  # requires DATABASE_URL
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
from batch.config import load_batch_settings
from batch.infrastructure.db import (
    ScaffoldDbWriter,
    create_db_writer,
    is_live_db_reader,
    resolve_job_db_reader,
)

_DEMO_RUN_ID = "scaffold-import-summary-run"


def build_scaffold_demo_job() -> ImportSummaryJob:
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
    )
    return ImportSummaryJob(repositories=repos)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-017 Import Summary creation")
    parser.add_argument("--job-run-id", default="local-run")
    parser.add_argument("--source-api", default="")
    parser.add_argument("--batch-run-id", default="")
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
        job = build_scaffold_demo_job()
        # demo seed の run id に合わせる
        result = job.run(
            job_run_id=batch_run_id if batch_run_id == _DEMO_RUN_ID else _DEMO_RUN_ID,
            source_api=source_api,
            batch_run_id=_DEMO_RUN_ID,
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
        or args.job_run_id
    )
    repos = ImportSummaryRepositories(
        db_writer=db_writer,
        db_reader=db_reader,
        seed_default_source_api=source_api,  # type: ignore[arg-type]
    )
    job = ImportSummaryJob(repositories=repos)
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
        f"phases={','.join(result.completed_phases)}"
    )
    return 0 if result.status in {"succeeded", "partially_succeeded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
