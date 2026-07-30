"""CLI entry for BATCH-006 商品差分判定 (scaffold / GHA invocation).

Usage:
  python -m batch.application.product_diff --job-run-id <id> [--max-items 100]
  python -m batch.application.product_diff --scaffold-demo
  python -m batch.application.product_diff \\
    --job-run-id <leaf-uuid> --batch-run-id <pipeline-uuid>
"""

from __future__ import annotations

import argparse
import sys

from batch.application.product_diff.job import (
    DEFAULT_MAX_ITEMS,
    DEFAULT_SOURCE,
    ProductDiffJob,
)
from batch.application.product_diff.models import ItemSeed, StagingItemSeed
from batch.application.product_diff.repositories import ProductDiffRepositories
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

# Fixed SHA-256 hex fixtures（再算出せず比較のみ）
_HASH_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
_HASH_B = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def _parse_csv(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or raw.strip() == "":
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _parse_bool(raw: str | None, *, default: bool) -> bool:
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_business_run_id(*, job_run_id: str, batch_run_id: str) -> str:
    """Shared pipeline UUID for obs / product_diff writes. Falls back to job_run_id."""

    return batch_run_id.strip() or job_run_id


def build_scaffold_demo_job(
    *,
    job_run_tracker: JobRunTracker | None = None,
    phase_log_writer: PhaseLogWriter | None = None,
    error_log_writer: ErrorLogWriter | None = None,
) -> ProductDiffJob:
    """Build an in-memory job for local / CI smoke without real secrets / Rakuten."""

    repos = ProductDiffRepositories(
        db_writer=ScaffoldDbWriter(),
        seed_staging=[
            StagingItemSeed(
                staging_item_id="si_demo_new",
                source="rakuten",
                external_item_code="shop:demo-new",
                normalized_hash=_HASH_A,
                item_name="Demo New Gift",
                item_url="https://item.example/shop/demo-new",
                price=3000,
                availability=1,
                diff_status=None,
            ),
            StagingItemSeed(
                staging_item_id="si_demo_updated",
                source="rakuten",
                external_item_code="shop:demo-updated",
                normalized_hash=_HASH_B,
                item_name="Demo Updated Gift",
                item_url="https://item.example/shop/demo-updated",
                price=4500,
                availability=1,
                diff_status=None,
            ),
        ],
        seed_items=[
            ItemSeed(
                source="rakuten",
                external_item_code="shop:demo-updated",
                normalized_hash=_HASH_A,
                item_id="it_demo_updated",
                item_name="Demo Updated Gift (old)",
                active_status="active",
            ),
        ],
        phase_log_writer=phase_log_writer,
        error_log_writer=error_log_writer,
    )
    return ProductDiffJob(repositories=repos,
job_run_tracker=job_run_tracker,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-006 Product diff judgment")
    parser.add_argument(
        "--job-run-id",
        default="local-run",
        help=(
            "Leaf job_run_id（tracker / batch_run_log PK）。"
            "Non --scaffold-demo Postgres tracker requires a UUID。"
        ),
    )
    parser.add_argument(
        "--batch-run-id",
        default="",
        help=(
            "共有 pipeline batch_run_id（obs bind / product_diff_result 書込）。"
            "未指定時は --job-run-id にフォールバック。"
        ),
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=DEFAULT_MAX_ITEMS,
        help="Max staging_item rows to judge (default 1000).",
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="source filter (default rakuten).",
    )
    parser.add_argument(
        "--staging-item-ids",
        default="",
        help="Comma-separated staging_item_id list (subset / re-run).",
    )
    parser.add_argument(
        "--external-item-codes",
        default="",
        help="Comma-separated external_item_code list (subset / re-run).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-judge even when staging_item.diff_status is already set.",
    )
    parser.add_argument(
        "--sync-staging-diff-status",
        default="true",
        help="Sync staging_item.diff_status after persist (default true).",
    )
    parser.add_argument(
        "--scaffold-demo",
        action="store_true",
        help="Run in-memory scaffold demo (no real DB / Rakuten).",
    )
    args = parser.parse_args(argv)
    business_run_id = _resolve_business_run_id(
        job_run_id=args.job_run_id, batch_run_id=args.batch_run_id
    )

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
        job.repositories.bind_run(batch_run_id=business_run_id)
        result = job.run(
            job_run_id=args.job_run_id,
            batch_run_id=business_run_id,
            max_items=args.max_items,
            source=args.source,
            staging_item_ids=_parse_csv(args.staging_item_ids),
            external_item_codes=_parse_csv(args.external_item_codes),
            force=args.force,
            sync_staging_diff_status=_parse_bool(
                args.sync_staging_diff_status, default=True
            ),
        )
        print(
            f"BATCH-006 scaffold demo status={result.status} "
            f"succeeded={len(result.succeeded_external_codes)} "
            f"failed={len(result.failed_external_codes)} "
            f"new={result.diff_new_count} "
            f"updated={result.diff_updated_count} "
            f"unchanged={result.diff_unchanged_count} "
            f"unavailable={result.diff_unavailable_count} "
            f"upserts={result.product_diff_upsert_count} "
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
            "DATABASE_URL is required for non --scaffold-demo BATCH-006 "
            "(DbReader postgres backend). Use --scaffold-demo for local/CI.",
            file=sys.stderr,
        )
        return 2

    repos = ProductDiffRepositories(db_writer=db_writer, db_reader=db_reader,
phase_log_writer=obs.phase_log_writer,
error_log_writer=obs.error_log_writer,
    )
    job = ProductDiffJob(repositories=repos,
job_run_tracker=tracker,
    )
    job.repositories.bind_run(batch_run_id=business_run_id)
    result = job.run(
        job_run_id=args.job_run_id,
        batch_run_id=business_run_id,
        max_items=args.max_items,
        source=args.source,
        staging_item_ids=_parse_csv(args.staging_item_ids),
        external_item_codes=_parse_csv(args.external_item_codes),
        force=args.force,
        sync_staging_diff_status=_parse_bool(
            args.sync_staging_diff_status, default=True
        ),
    )
    print(
        f"BATCH-006 status={result.status} "
        f"db_reader={db_reader.backend} "
        f"db_writer={db_writer.backend} "
        f"succeeded={len(result.succeeded_external_codes)} "
        f"failed={len(result.failed_external_codes)} "
        f"upserts={result.product_diff_upsert_count}"
    )
    return 0 if result.status in {"succeeded", "partially_succeeded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
