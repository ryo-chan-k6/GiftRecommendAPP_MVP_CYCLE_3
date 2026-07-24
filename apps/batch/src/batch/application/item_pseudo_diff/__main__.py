"""CLI entry for BATCH-003 item pseudo-diff (scaffold / GHA invocation).

Usage:
  python -m batch.application.item_pseudo_diff --job-run-id <id> [--genre-ids 100]
  python -m batch.application.item_pseudo_diff --scaffold-demo
"""

from __future__ import annotations

import argparse
import sys

from batch.application.item_pseudo_diff.job import (
    DEFAULT_TARGET_GENRE_IDS,
    ItemPseudoDiffJob,
)
from batch.application.item_pseudo_diff.models import FetchCursorRow
from batch.application.item_pseudo_diff.repositories import ItemPseudoDiffRepositories
from batch.config import load_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter, create_db_writer
from batch.infrastructure.object_storage import ScaffoldObjectStorageClient
from batch.infrastructure.rakuten import RakutenItem, ScaffoldRakutenApiClient


def _parse_csv(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or raw.strip() == "":
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def build_scaffold_demo_job() -> ItemPseudoDiffJob:
    """Build an in-memory job for local / CI smoke without real secrets."""

    client = ScaffoldRakutenApiClient(
        items=(
            RakutenItem(item_code="shop:demo-1", item_name="Demo Item 1"),
            RakutenItem(item_code="shop:demo-2", item_name="Demo Item 2"),
        ),
        item_search_raw_responses={
            ("genre", "100", 1): {
                "Items": [
                    {"Item": {"itemCode": "shop:demo-1", "itemName": "Demo Item 1"}},
                    {"Item": {"itemCode": "shop:demo-2", "itemName": "Demo Item 2"}},
                ]
            },
            ("update_sort", "*", 1): {
                "Items": [
                    {"Item": {"itemCode": "shop:demo-1", "itemName": "Demo Item 1"}},
                ]
            },
            ("ranking_supplement", "shop:unknown-rank", 1): {
                "Items": [
                    {
                        "Item": {
                            "itemCode": "shop:unknown-rank",
                            "itemName": "From Ranking Supplement",
                        }
                    }
                ]
            },
        },
    )
    repos = ItemPseudoDiffRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=ScaffoldDbWriter(),
        bucket="scaffold-raw",
        seed_cursors=[
            FetchCursorRow(
                cursor_type="ranking_supplement",
                scope={"external_item_code": "shop:unknown-rank"},
                page=1,
                cursor_status="active",
            )
        ],
    )
    return ItemPseudoDiffJob(rakuten_client=client, repositories=repos)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-003 Rakuten item pseudo-diff")
    parser.add_argument("--job-run-id", default="local-run")
    parser.add_argument(
        "--genre-ids",
        default="",
        help="Comma-separated genre IDs. Empty uses default fetch_plan placeholder.",
    )
    parser.add_argument(
        "--keywords",
        default="",
        help="Comma-separated keywords (optional MVP route).",
    )
    parser.add_argument(
        "--scaffold-demo",
        action="store_true",
        help="Run in-memory scaffold demo (no real Rakuten/DB/Object Storage).",
    )
    args = parser.parse_args(argv)

    if args.scaffold_demo:
        job = build_scaffold_demo_job()
        genre_ids = _parse_csv(args.genre_ids) or DEFAULT_TARGET_GENRE_IDS
        keywords = _parse_csv(args.keywords)
        result = job.run(
            job_run_id=args.job_run_id,
            target_genre_ids=genre_ids,
            keywords=keywords,
        )
        print(
            f"BATCH-003 scaffold demo status={result.status} "
            f"succeeded={len(result.succeeded_cursor_ids)} "
            f"failed={len(result.failed_cursor_ids)} "
            f"raw_saves={result.raw_save_success_count} "
            f"candidates={result.candidate_item_code_count} "
            f"supplement={result.ranking_supplement_consumed_count}"
        )
        return 0 if result.status in {"succeeded", "partially_succeeded"} else 1

    settings = load_batch_settings()
    db_writer = create_db_writer(settings.database_url)
    if not settings.rakuten_application_id:
        print(
            "RAKUTEN_APPLICATION_ID is required for non-scaffold runs. "
            "Use --scaffold-demo for local/CI.",
            file=sys.stderr,
        )
        return 2

    print(
        f"DbWriter backend={db_writer.backend} is resolved, "
        "but real Rakuten HTTP client is not enabled yet. "
        "Use --scaffold-demo, or extend infrastructure after Human Review.",
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
