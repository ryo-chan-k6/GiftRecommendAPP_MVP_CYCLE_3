"""CLI entry for BATCH-008 item active status apply (scaffold / GHA invocation).

Usage:
  python -m batch.application.item_active_status --scaffold-demo
  python -m batch.application.item_active_status --job-run-id <id> --scaffold-demo
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from batch.application.item_active_status.job import ItemActiveStatusJob
from batch.application.item_active_status.models import CandidateRow, DiffSuggestion, ItemRow
from batch.application.item_active_status.repositories import ItemActiveStatusRepositories
from batch.infrastructure.db import ScaffoldDbWriter


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-008 Item Active Status Updater")
    parser.add_argument("--job-run-id", default="local-run")
    parser.add_argument(
        "--scaffold-demo",
        action="store_true",
        help="Run in-memory scaffold demo (no real DB).",
    )
    args = parser.parse_args(argv)

    if not args.scaffold_demo:
        print(
            "Real DB client is not enabled in this Task. "
            "Use --scaffold-demo for local/CI.",
        )
        return 3

    job = build_scaffold_demo_job()
    result = job.run(job_run_id=args.job_run_id)
    print(
        f"BATCH-008 scaffold demo status={result.status} "
        f"updated={result.item_status_updated_count} "
        f"applied={result.candidate_applied_count} "
        f"superseded={result.candidate_superseded_count} "
        f"reactivations={result.reactivation_count} "
        f"failed={len(result.failed_item_codes)}"
    )
    return 0 if result.status in {"succeeded", "partially_succeeded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
