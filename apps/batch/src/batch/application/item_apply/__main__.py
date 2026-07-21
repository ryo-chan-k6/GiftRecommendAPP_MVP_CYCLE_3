"""CLI entry for BATCH-007 Item反映 (scaffold / GHA invocation).

Usage:
  python -m batch.application.item_apply --job-run-id <id> [--max-items 100]
  python -m batch.application.item_apply --scaffold-demo
"""

from __future__ import annotations

import argparse
import sys

from batch.application.item_apply.job import (
    DEFAULT_MAX_ITEMS,
    DEFAULT_SOURCE,
    ItemApplyJob,
)
from batch.application.item_apply.models import (
    ItemSeed,
    ProductDiffResultSeed,
    StagingImageSeed,
    StagingItemSeed,
)
from batch.application.item_apply.repositories import ItemApplyRepositories
from batch.config import load_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter

_HASH_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
_HASH_B = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def _parse_csv(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or raw.strip() == "":
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def build_scaffold_demo_job() -> ItemApplyJob:
    """Build an in-memory job for local / CI smoke without real secrets / Rakuten."""

    repos = ItemApplyRepositories(
        db_writer=ScaffoldDbWriter(),
        seed_diffs=[
            ProductDiffResultSeed(
                product_diff_result_id="pdr_demo_new",
                batch_run_id="diff-run-demo",
                staging_item_id="si_demo_new",
                external_item_code="shop:demo-new",
                diff_status="new",
                old_hash=None,
                new_hash=_HASH_A,
            ),
            ProductDiffResultSeed(
                product_diff_result_id="pdr_demo_updated",
                batch_run_id="diff-run-demo",
                staging_item_id="si_demo_updated",
                external_item_code="shop:demo-updated",
                diff_status="updated",
                old_hash=_HASH_A,
                new_hash=_HASH_B,
            ),
        ],
        seed_staging=[
            StagingItemSeed(
                staging_item_id="si_demo_new",
                source="rakuten",
                external_item_code="shop:demo-new",
                normalized_hash=_HASH_A,
                item_name="Demo New Gift",
                item_url="https://item.example/shop/demo-new",
                price=3000,
                review_average=4.5,
                review_count=10,
            ),
            StagingItemSeed(
                staging_item_id="si_demo_updated",
                source="rakuten",
                external_item_code="shop:demo-updated",
                normalized_hash=_HASH_B,
                item_name="Demo Updated Gift",
                item_url="https://item.example/shop/demo-updated",
                price=4500,
            ),
        ],
        seed_images=[
            StagingImageSeed(
                staging_item_id="si_demo_new",
                image_url="https://img.example/demo-new.jpg",
                image_size_type="medium",
                display_order=0,
                is_primary_candidate=True,
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
                is_active=True,
            ),
        ],
    )
    return ItemApplyJob(repositories=repos)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-007 Item apply")
    parser.add_argument("--job-run-id", default="local-run")
    parser.add_argument(
        "--max-items",
        type=int,
        default=DEFAULT_MAX_ITEMS,
        help="Max product_diff_result rows to apply (default 1000).",
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="source filter via staging (default rakuten).",
    )
    parser.add_argument(
        "--diff-batch-run-id",
        default="",
        help="Consume product_diff_result for this BATCH-006 batch_run_id.",
    )
    parser.add_argument(
        "--external-item-codes",
        default="",
        help="Comma-separated external_item_code list (subset / re-run).",
    )
    parser.add_argument(
        "--staging-item-ids",
        default="",
        help="Comma-separated staging_item_id list (subset / re-run).",
    )
    parser.add_argument(
        "--scaffold-demo",
        action="store_true",
        help="Run in-memory scaffold demo (no real DB / Rakuten).",
    )
    args = parser.parse_args(argv)

    if args.scaffold_demo:
        job = build_scaffold_demo_job()
        result = job.run(
            job_run_id=args.job_run_id,
            max_items=args.max_items,
            source=args.source,
            diff_batch_run_id=args.diff_batch_run_id or None,
            external_item_codes=_parse_csv(args.external_item_codes),
            staging_item_ids=_parse_csv(args.staging_item_ids),
        )
        print(
            f"BATCH-007 scaffold demo status={result.status} "
            f"succeeded={len(result.succeeded_external_codes)} "
            f"failed={len(result.failed_external_codes)} "
            f"upserts={result.item_upsert_count} "
            f"unchanged_touch={result.item_unchanged_touch_count} "
            f"unavailable_skip={result.item_unavailable_skip_count} "
            f"phases={','.join(result.completed_phases)}"
        )
        return 0 if result.status in {"succeeded", "partially_succeeded"} else 1

    settings = load_batch_settings()
    _ = settings  # real wiring is out of this Task (scaffold-first)
    print(
        "Real DB client is not enabled in this Task. "
        "Use --scaffold-demo for local/CI.",
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
