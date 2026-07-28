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
from batch.application.job_run import JobRunTracker, create_job_run_tracker
from batch.application.observability import (
    ApiCallLogWriter,
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
from batch.infrastructure.object_storage import (
    ScaffoldObjectStorageClient,
    create_object_storage_client,
    missing_live_object_storage_credentials,
    resolve_live_object_storage_flag,
)
from batch.infrastructure.rakuten import (
    ScaffoldRakutenApiClient,
    create_rakuten_client,
    resolve_live_rakuten_flag,
)


def _parse_csv(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or raw.strip() == "":
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def build_scaffold_demo_job(
    *,
    job_run_tracker: JobRunTracker | None = None,
    phase_log_writer: PhaseLogWriter | None = None,
    error_log_writer: ErrorLogWriter | None = None,
    api_call_log_writer: ApiCallLogWriter | None = None,
) -> ItemRecheckJob:
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
        phase_log_writer=phase_log_writer,
        error_log_writer=error_log_writer,
        api_call_log_writer=api_call_log_writer,
    )
    return ItemRecheckJob(rakuten_client=client, repositories=repos,
job_run_tracker=job_run_tracker,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-004 Rakuten existing-item recheck")
    parser.add_argument(
        "--job-run-id",
        default="local-run",
        help="Job run id. Non --scaffold-demo Postgres tracker requires a UUID.",
    )
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
    parser.add_argument(
        "--live-object-storage",
        action="store_true",
        help=(
            "Enable real S3-compatible Object Storage (requires OBJECT_STORAGE_*). "
            "Default off; also BATCH_OBJECT_STORAGE_LIVE."
        ),
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
            api_call_log_writer=obs.api_call_log_writer,
        )
        job.repositories.bind_run(batch_run_id=args.job_run_id)
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
            "DATABASE_URL is required for non --scaffold-demo BATCH-004 "
            "(DbReader postgres backend). Use --scaffold-demo for local/CI.",
            file=sys.stderr,
        )
        return 2

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

    storage_live = resolve_live_object_storage_flag(
        cli_live=args.live_object_storage,
        env_value=os.environ.get("BATCH_OBJECT_STORAGE_LIVE"),
    )
    if storage_live:
        missing = missing_live_object_storage_credentials(
            access_key=settings.object_storage_access_key,
            secret_key=settings.object_storage_secret_key,
            endpoint=settings.object_storage_endpoint,
        )
        if missing:
            print(missing, file=sys.stderr)
            return 2
    object_storage = create_object_storage_client(
        settings.object_storage_access_key,
        settings.object_storage_secret_key,
        endpoint=settings.object_storage_endpoint,
        live=storage_live,
    )

    rakuten = create_rakuten_client(
        settings.rakuten_application_id,
        settings.rakuten_access_key,
        live=True,
    )
    repos = ItemRecheckRepositories(
        object_storage=object_storage,
        db_writer=db_writer,
        db_reader=db_reader,
        bucket=settings.object_storage_bucket or "scaffold-raw",
        phase_log_writer=obs.phase_log_writer,
        error_log_writer=obs.error_log_writer,
        api_call_log_writer=obs.api_call_log_writer,
    )
    job = ItemRecheckJob(rakuten_client=rakuten, repositories=repos,
job_run_tracker=tracker,
    )
    job.repositories.bind_run(batch_run_id=args.job_run_id)
    codes = _parse_csv(args.external_item_codes)
    result = job.run(
        job_run_id=args.job_run_id,
        max_items=args.max_items,
        external_item_codes=codes or None,
    )
    print(
        f"BATCH-004 status={result.status} "
        f"db_reader={db_reader.backend} "
        f"db_writer={db_writer.backend} "
        f"rakuten_backend={getattr(rakuten, 'backend', 'http')} "
        f"storage_backend={getattr(object_storage, 'backend', 'scaffold')} "
        f"succeeded={len(result.succeeded_item_codes)} "
        f"failed={len(result.failed_item_codes)}"
    )
    return 0 if result.status in {"succeeded", "partially_succeeded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
