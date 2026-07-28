"""CLI entry for BATCH-010 Item Semantic 生成 (scaffold / GHA invocation).

Usage:
  python -m batch.application.item_semantic --job-run-id <id> [--max-items 1000]
  python -m batch.application.item_semantic --scaffold-demo
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

from batch.application.item_semantic.job import (
    DEFAULT_MAX_ITEMS,
    DEFAULT_QUEUE_BATCH_SIZE,
    DEFAULT_SOURCE,
    ItemSemanticJob,
    build_default_scaffold_job,
)
from batch.application.item_semantic.models import ItemContext, QueueRow
from batch.application.item_semantic.repositories import ItemSemanticRepositories
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

_NOW = datetime(2026, 7, 17, 12, 0, 0, tzinfo=UTC)


def _parse_csv(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or raw.strip() == "":
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def build_scaffold_demo_job(
    *,
    job_run_tracker: JobRunTracker | None = None,
    phase_log_writer: PhaseLogWriter | None = None,
    error_log_writer: ErrorLogWriter | None = None,
) -> ItemSemanticJob:
    """Build an in-memory job for local / CI smoke without real secrets / DB."""

    repos = ItemSemanticRepositories(
        db_writer=ScaffoldDbWriter(),
        seed_queues=[
            QueueRow(
                item_generation_queue_id="igq_demo_semantic",
                item_id="it_demo_1",
                generation_type="semantic",
                queue_status="queued",
                queued_at=_NOW,
            ),
            QueueRow(
                item_generation_queue_id="igq_demo_feature",
                item_id="it_demo_2",
                generation_type="feature",
                queue_status="queued",
                queued_at=_NOW,
            ),
        ],
        seed_items=[
            ItemContext(
                item_id="it_demo_1",
                source="rakuten",
                external_item_code="shop:demo-1",
                active_status="active",
                is_active=True,
                item_name="Demo Gift Semantic",
                genre_name="ギフト",
                attributes=("包装あり",),
                tags=("季節",),
            ),
            ItemContext(
                item_id="it_demo_2",
                source="rakuten",
                external_item_code="shop:demo-2",
                active_status="active",
                is_active=True,
                item_name="Demo Feature Only",
            ),
        ],
        phase_log_writer=phase_log_writer,
        error_log_writer=error_log_writer,
    )
    return build_default_scaffold_job(repos, job_run_tracker=job_run_tracker)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-010 Item Semantic generation")
    parser.add_argument(
        "--job-run-id",
        default="local-run",
        help="Job run id. Non --scaffold-demo Postgres tracker requires a UUID.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=DEFAULT_MAX_ITEMS,
        help="Max queue rows to claim (default 1000).",
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="source filter via item (default rakuten).",
    )
    parser.add_argument(
        "--queue-batch-size",
        type=int,
        default=DEFAULT_QUEUE_BATCH_SIZE,
        help="Claim batch size (default 100).",
    )
    parser.add_argument(
        "--item-ids",
        default="",
        help="Comma-separated item_id list (subset / re-run).",
    )
    parser.add_argument(
        "--queue-ids",
        default="",
        help="Comma-separated item_generation_queue_id list.",
    )
    parser.add_argument(
        "--scaffold-demo",
        action="store_true",
        help="Run in-memory scaffold demo (no real DB).",
    )
    args = parser.parse_args(argv)

    if args.scaffold_demo:
        tracker = create_job_run_tracker(scaffold_demo=True, database_url=None)
        obs = create_batch_observability_writers(
            scaffold_demo=True, database_url=None
        )
        job = build_scaffold_demo_job(
            job_run_tracker=tracker,
            phase_log_writer=obs.phase_log_writer,
            error_log_writer=obs.error_log_writer,
        )
        job.repositories.bind_run(batch_run_id=args.job_run_id)
        result = job.run(
            job_run_id=args.job_run_id,
            max_items=args.max_items,
            source=args.source,
            queue_batch_size=args.queue_batch_size,
            item_ids=_parse_csv(args.item_ids),
            queue_ids=_parse_csv(args.queue_ids),
        )
        print(
            f"BATCH-010 scaffold demo status={result.status} "
            f"claimed={result.claimed_count} "
            f"generated={result.semantic_generated_count} "
            f"skipped={result.semantic_skipped_count} "
            f"failed={result.semantic_failed_count} "
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
            "DATABASE_URL is required for non --scaffold-demo BATCH-010 "
            "(DbReader postgres backend). Use --scaffold-demo for local/CI.",
            file=sys.stderr,
        )
        return 2

    repos = ItemSemanticRepositories(
        db_writer=db_writer,
        db_reader=db_reader,
        phase_log_writer=obs.phase_log_writer,
        error_log_writer=obs.error_log_writer,
    )
    job = build_default_scaffold_job(repos, job_run_tracker=tracker)
    job.repositories.bind_run(batch_run_id=args.job_run_id)
    result = job.run(
        job_run_id=args.job_run_id,
        max_items=args.max_items,
        source=args.source,
        queue_batch_size=args.queue_batch_size,
        item_ids=_parse_csv(args.item_ids),
        queue_ids=_parse_csv(args.queue_ids),
    )
    print(
        f"BATCH-010 status={result.status} "
        f"db_reader={db_reader.backend} "
        f"db_writer={db_writer.backend} "
        f"claimed={result.claimed_count} "
        f"generated={result.semantic_generated_count} "
        f"skipped={result.semantic_skipped_count} "
        f"failed={result.semantic_failed_count} "
        f"phases={','.join(result.completed_phases)}"
    )
    return 0 if result.status in {"succeeded", "partially_succeeded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
