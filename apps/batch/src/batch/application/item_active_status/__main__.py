"""CLI entry for BATCH-008 item active status apply / T7 Retention (scaffold).

Usage:
  python -m batch.application.item_active_status --job-run-id <id> [--max-items 100]
  python -m batch.application.item_active_status --scaffold-demo
  python -m batch.application.item_active_status --retention-cleanup --scaffold-demo
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone

from batch.application.item_active_status.job import (
    DEFAULT_MAX_ITEMS,
    DEFAULT_SOURCE,
    ItemActiveStatusJob,
)
from batch.application.item_active_status.models import CandidateRow, DiffSuggestion, ItemRow
from batch.application.item_active_status.repositories import ItemActiveStatusRepositories
from batch.application.item_active_status.retention import RetentionCleanupJob
from batch.config import load_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter, create_db_writer


def _parse_csv(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or raw.strip() == "":
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def build_scaffold_demo_job() -> ItemActiveStatusJob:
    """Build an in-memory job for local / CI smoke without real DB secrets."""

    now = datetime.now(timezone.utc)
    repos = ItemActiveStatusRepositories(db_writer=ScaffoldDbWriter())
    repos.seed_item(
        ItemRow(
            source="rakuten",
            external_item_code="shop:demo-1",
            active_status="active",
            item_id="item-demo-1",
        )
    )
    repos.seed_item(
        ItemRow(
            source="rakuten",
            external_item_code="shop:demo-2",
            active_status="unavailable",
            item_id="item-demo-2",
        )
    )
    repos.seed_diff(
        DiffSuggestion(
            product_diff_result_id="diff-1",
            batch_run_id="run-demo",
            source="rakuten",
            external_item_code="shop:demo-1",
            diff_status="unavailable",
            proposed_active_status="unavailable",
            judged_at=now - timedelta(hours=1),
        )
    )
    repos.seed_candidate(
        CandidateRow(
            candidate_id="cand-1",
            batch_run_id="run-demo",
            source="rakuten",
            external_item_code="shop:demo-1",
            candidate_active_status="inactive",
            candidate_status="detected",
            detected_at=now,
            detection_basis="availability",
            reason_code="availability_zero",
        )
    )
    repos.seed_candidate(
        CandidateRow(
            candidate_id="cand-2",
            batch_run_id="run-demo",
            source="rakuten",
            external_item_code="shop:demo-2",
            candidate_active_status="active",
            candidate_status="detected",
            detected_at=now,
            detection_basis="api_success",
            reason_code="available",
        )
    )
    return ItemActiveStatusJob(repositories=repos)


def build_scaffold_retention_job() -> RetentionCleanupJob:
    """Seed terminal + detected rows for Retention smoke."""

    now = datetime.now(timezone.utc)
    repos = ItemActiveStatusRepositories(db_writer=ScaffoldDbWriter())
    old = now - timedelta(days=20)
    young = now - timedelta(days=2)
    repos.seed_candidate(
        CandidateRow(
            candidate_id="ret-detected",
            batch_run_id="run-ret",
            source="rakuten",
            external_item_code="shop:ret-d",
            candidate_active_status="unavailable",
            candidate_status="detected",
            detected_at=old,
        )
    )
    repos.seed_candidate(
        CandidateRow(
            candidate_id="ret-applied-old",
            batch_run_id="run-ret",
            source="rakuten",
            external_item_code="shop:ret-a",
            candidate_active_status="unavailable",
            candidate_status="applied",
            detected_at=old,
            applied_at=old,
            updated_at=old,
        )
    )
    repos.seed_candidate(
        CandidateRow(
            candidate_id="ret-superseded-young",
            batch_run_id="run-ret",
            source="rakuten",
            external_item_code="shop:ret-s",
            candidate_active_status="inactive",
            candidate_status="superseded",
            detected_at=young,
            updated_at=young,
        )
    )
    return RetentionCleanupJob(repositories=repos)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-008 Item Active Status / Retention")
    parser.add_argument("--job-run-id", default="local-run")
    parser.add_argument(
        "--max-items",
        type=int,
        default=DEFAULT_MAX_ITEMS,
        help="Max item keys to apply (default 1000).",
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="source filter (default rakuten).",
    )
    parser.add_argument(
        "--batch-run-id",
        default="",
        help="Filter Diff / candidate by this batch_run_id.",
    )
    parser.add_argument(
        "--external-item-codes",
        default="",
        help="Comma-separated external_item_code list (subset / re-run).",
    )
    parser.add_argument(
        "--scaffold-demo",
        action="store_true",
        help="Run in-memory scaffold demo (no real DB).",
    )
    parser.add_argument(
        "--retention-cleanup",
        action="store_true",
        help="Run T7 Retention cleanup instead of Applier (scaffold only).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Retention only: count eligible rows without DELETE.",
    )
    args = parser.parse_args(argv)

    if not args.scaffold_demo:
        settings = load_batch_settings()
        db_writer = create_db_writer(settings.database_url)
        print(
            f"DbWriter backend={db_writer.backend} is resolved, "
            "but real DB read path is not enabled yet. "
            "Use --scaffold-demo for local/CI.",
            file=sys.stderr,
        )
        return 3

    if args.retention_cleanup:
        # T7 is out of BATCH-008 Epic production scope (§18.1 No.11).
        # Keep scaffold path for local smoke / existing UT harness.
        job = build_scaffold_retention_job()
        result = job.run(job_run_id=args.job_run_id, dry_run=args.dry_run)
        print(
            f"T7 retention status={result.status} "
            f"deleted={result.deleted_count} "
            f"skipped_detected={result.skipped_detected_count} "
            f"skipped_young={result.skipped_young_count} "
            f"dry_run={args.dry_run}"
        )
        return 0 if result.status in {"succeeded", "partially_succeeded"} else 1

    job = build_scaffold_demo_job()
    result = job.run(
        job_run_id=args.job_run_id,
        max_items=args.max_items,
        source=args.source,
        batch_run_id=args.batch_run_id or None,
        external_item_codes=_parse_csv(args.external_item_codes),
    )
    print(
        f"BATCH-008 scaffold demo status={result.status} "
        f"updated={result.item_status_updated_count} "
        f"applied={result.candidate_applied_count} "
        f"superseded={result.candidate_superseded_count} "
        f"reactivations={result.reactivation_count} "
        f"failed={len(result.failed_item_codes)} "
        f"phases={','.join(result.completed_phases)}"
    )
    return 0 if result.status in {"succeeded", "partially_succeeded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
