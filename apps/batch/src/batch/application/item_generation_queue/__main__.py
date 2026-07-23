"""CLI entry for BATCH-009 商品意味生成キュー登録 (scaffold / GHA invocation).

Usage:
  python -m batch.application.item_generation_queue --job-run-id <id> [--max-items 1000]
  python -m batch.application.item_generation_queue --scaffold-demo
"""

from __future__ import annotations

import argparse
import sys

from batch.application.item_generation_queue.job import (
    DEFAULT_MAX_ITEMS,
    DEFAULT_SOURCE,
    ItemGenerationQueueJob,
)
from batch.application.item_generation_queue.models import ItemRow, MeaningSnapshot, ProductDiffRow
from batch.application.item_generation_queue.repositories import ItemGenerationQueueRepositories
from batch.config import load_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter, create_db_writer

_HASH_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
_HASH_B = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def _parse_csv(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or raw.strip() == "":
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def build_scaffold_demo_job() -> ItemGenerationQueueJob:
    """Build an in-memory job for local / CI smoke without real secrets / DB."""

    repos = ItemGenerationQueueRepositories(
        db_writer=ScaffoldDbWriter(),
        seed_diffs=[
            ProductDiffRow(
                product_diff_result_id="pdr_demo_new",
                batch_run_id="diff-run-demo",
                staging_item_id="si_demo_new",
                external_item_code="shop:demo-new",
                diff_status="new",
                new_hash=_HASH_A,
            ),
            ProductDiffRow(
                product_diff_result_id="pdr_demo_meaning",
                batch_run_id="diff-run-demo",
                staging_item_id="si_demo_meaning",
                external_item_code="shop:demo-meaning",
                diff_status="updated",
                old_hash=_HASH_A,
                new_hash=_HASH_B,
                previous_meaning=MeaningSnapshot(item_name="Old Name"),
            ),
        ],
        seed_items=[
            ItemRow(
                item_id="it_demo_new",
                source="rakuten",
                external_item_code="shop:demo-new",
                active_status="active",
                is_active=True,
                normalized_hash=_HASH_A,
                item_name="Demo New Gift",
            ),
            ItemRow(
                item_id="it_demo_meaning",
                source="rakuten",
                external_item_code="shop:demo-meaning",
                active_status="active",
                is_active=True,
                normalized_hash=_HASH_B,
                item_name="Updated Meaning Gift",
            ),
        ],
    )
    return ItemGenerationQueueJob(repositories=repos)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-009 Item generation queue registration")
    parser.add_argument("--job-run-id", default="local-run")
    parser.add_argument(
        "--max-items",
        type=int,
        default=DEFAULT_MAX_ITEMS,
        help="Max product_diff_result rows to evaluate (default 1000).",
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="source filter via item (default rakuten).",
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
        "--scaffold-demo",
        action="store_true",
        help="Run in-memory scaffold demo (no real DB).",
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
        )
        print(
            f"BATCH-009 scaffold demo status={result.status} "
            f"succeeded={len(result.succeeded_external_codes)} "
            f"failed={len(result.failed_external_codes)} "
            f"skipped={len(result.skipped_external_codes)} "
            f"inserted={result.queue_inserted_count} "
            f"queued_at_touch={result.queue_queued_at_updated_count} "
            f"semantic={result.queue_semantic_count} "
            f"phases={','.join(result.completed_phases)}"
        )
        return 0 if result.status in {"succeeded", "partially_succeeded"} else 1

    settings = load_batch_settings()
    db_writer = create_db_writer(settings.database_url)
    print(
        f"DbWriter backend={db_writer.backend} is resolved, "
        "but real DB read path is not enabled yet. "
        "Use --scaffold-demo for local/CI.",
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
