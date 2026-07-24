"""CLI entry for BATCH-004 existing-item recheck (scaffold / GHA invocation).

Usage:
  python -m batch.application.item_recheck --job-run-id <id> [--max-items 100]
  python -m batch.application.item_recheck --scaffold-demo
"""

from __future__ import annotations

import argparse
import sys

from batch.application.item_recheck.job import ItemRecheckJob
from batch.application.item_recheck.models import ItemSeed
from batch.application.item_recheck.repositories import ItemRecheckRepositories
from batch.config import load_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter, create_db_writer
from batch.infrastructure.object_storage import ScaffoldObjectStorageClient
from batch.infrastructure.rakuten import (
    ScaffoldRakutenApiClient,
    create_rakuten_client,
    resolve_live_rakuten_flag,
)


def _parse_csv(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or raw.strip() == "":
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def build_scaffold_demo_job() -> ItemRecheckJob:
    """Build an in-memory job for local / CI smoke without real secrets."""

    client = ScaffoldRakutenApiClient(
        item_search_raw_responses={
            ("recheck", "shop:demo-1", 1): {
                "Items": [
                    {
                        "Item": {
                            "itemCode": "shop:demo-1",
                            "itemName": "Demo Recheck Item",
                            "availability": 1,
                        }
                    }
                ]
            },
            ("recheck", "shop:demo-empty", 1): {"Items": []},
            ("recheck", "shop:demo-zero", 1): {
                "Items": [
                    {
                        "Item": {
                            "itemCode": "shop:demo-zero",
                            "itemName": "Unavailable",
                            "availability": 0,
                        }
                    }
                ]
            },
        },
    )
    repos = ItemRecheckRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=ScaffoldDbWriter(),
        bucket="scaffold-raw",
        seed_items=[
            ItemSeed(
                source="rakuten",
                external_item_code="shop:demo-1",
                item_id="item_demo_1",
                active_status="active",
            ),
            ItemSeed(
                source="rakuten",
                external_item_code="shop:demo-empty",
                item_id="item_demo_empty",
                active_status="active",
            ),
            ItemSeed(
                source="rakuten",
                external_item_code="shop:demo-zero",
                item_id="item_demo_zero",
                active_status="active",
            ),
        ],
    )
    return ItemRecheckJob(rakuten_client=client, repositories=repos)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-004 Rakuten existing-item recheck")
    parser.add_argument("--job-run-id", default="local-run")
    parser.add_argument(
        "--max-items",
        type=int,
        default=1000,
        help="Max items to recheck in this run (default 1000).",
    )
    parser.add_argument(
        "--external-item-codes",
        default="",
        help="Comma-separated external_item_code list (overrides priority).",
    )
    parser.add_argument(
        "--scaffold-demo",
        action="store_true",
        help="Run in-memory scaffold demo (no real Rakuten/DB/Object Storage).",
    )
    parser.add_argument(
        "--live-rakuten",
        action="store_true",
        help="Enable real Rakuten HTTP (requires secrets). Default off; also BATCH_RAKUTEN_LIVE.",
    )
    args = parser.parse_args(argv)

    if args.scaffold_demo:
        job = build_scaffold_demo_job()
        codes = _parse_csv(args.external_item_codes)
        result = job.run(
            job_run_id=args.job_run_id,
            max_items=args.max_items,
            external_item_codes=codes,
        )
        print(
            f"BATCH-004 scaffold demo status={result.status} "
            f"succeeded={len(result.succeeded_item_codes)} "
            f"failed={len(result.failed_item_codes)} "
            f"raw_saves={result.raw_save_success_count} "
            f"candidates={result.candidate_upsert_count} "
            f"empty_hits={result.empty_hit_count}"
        )
        return 0 if result.status in {"succeeded", "partially_succeeded"} else 1

    import os

    settings = load_batch_settings()
    db_writer = create_db_writer(settings.database_url)
    live = resolve_live_rakuten_flag(
        cli_live=args.live_rakuten,
        env_value=os.environ.get("BATCH_RAKUTEN_LIVE"),
    )
    if not live:
        print(
            "Rakuten live is disabled (default). "
            "Pass --live-rakuten or set BATCH_RAKUTEN_LIVE=1. "
            "Use --scaffold-demo for local/CI without secrets.",
            file=sys.stderr,
        )
        return 3
    if not settings.rakuten_application_id or not settings.rakuten_access_key:
        print(
            "RAKUTEN_APPLICATION_ID and RAKUTEN_ACCESS_KEY are required for --live-rakuten. "
            "Use --scaffold-demo for local/CI.",
            file=sys.stderr,
        )
        return 2

    rakuten = create_rakuten_client(
        settings.rakuten_application_id,
        settings.rakuten_access_key,
        live=True,
    )
    # seed 空: 実 DB SELECT は未実装。配線確認は 0 件成功で可。
    repos = ItemRecheckRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=db_writer,
        bucket=settings.object_storage_bucket or "scaffold-raw",
    )
    job = ItemRecheckJob(rakuten_client=rakuten, repositories=repos)
    codes = _parse_csv(args.external_item_codes)
    result = job.run(
        job_run_id=args.job_run_id,
        max_items=args.max_items,
        external_item_codes=codes or None,
    )
    print(
        f"BATCH-004 status={result.status} "
        f"db_backend={db_writer.backend} "
        f"rakuten_backend={getattr(rakuten, 'backend', 'http')} "
        f"succeeded={len(result.succeeded_item_codes)} "
        f"failed={len(result.failed_item_codes)}"
    )
    return 0 if result.status in {"succeeded", "partially_succeeded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
