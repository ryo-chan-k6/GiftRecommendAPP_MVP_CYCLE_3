"""CLI entry for BATCH-005 Raw取込・Staging変換 (scaffold / GHA invocation).

Usage:
  python -m batch.application.raw_staging --job-run-id <id> [--max-raw 100]
  python -m batch.application.raw_staging --scaffold-demo
"""

from __future__ import annotations

import argparse
import json
import sys

from batch.application.raw_staging.hashing import content_hash_for_bytes
from batch.application.raw_staging.job import RawStagingJob
from batch.application.raw_staging.models import RawMetadataSeed
from batch.application.raw_staging.repositories import RawStagingRepositories
from batch.config import load_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter, create_db_writer
from batch.infrastructure.object_storage import (
    ObjectRef,
    ScaffoldObjectStorageClient,
    create_object_storage_client,
    missing_live_object_storage_credentials,
    resolve_live_object_storage_flag,
)

DEMO_OBJECT_KEY = "raw/rakuten/item_search/dt=2026-07-15/batch_run_id=demo/demo-item.json"
DEMO_RAW_ID = "rm_demo_item_search_1"


def _demo_item_search_payload() -> dict[str, object]:
    return {
        "Items": [
            {
                "Item": {
                    "itemCode": "shop:demo-gift-1",
                    "itemName": "Demo Gift Box",
                    "itemCaption": "A demo gift for staging",
                    "catchcopy": "Perfect gift",
                    "itemPrice": 3980,
                    "itemUrl": "https://item.example/shop/demo-gift-1",
                    "genreId": 101240,
                    "shopCode": "shop",
                    "availability": 1,
                    "reviewAverage": 4.5,
                    "reviewCount": 12,
                    "attributeIds": ["1001", "1002"],
                    "mediumImageUrls": [
                        {"imageUrl": "https://img.example/medium/1.jpg"},
                        {"imageUrl": "https://img.example/medium/2.jpg"},
                    ],
                    "smallImageUrls": [{"imageUrl": "https://img.example/small/1.jpg"}],
                }
            }
        ]
    }


def _parse_csv(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or raw.strip() == "":
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def build_scaffold_demo_job() -> RawStagingJob:
    """Build an in-memory job for local / CI smoke without real secrets."""

    payload = _demo_item_search_payload()
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    content_hash = content_hash_for_bytes(body)

    storage = ScaffoldObjectStorageClient()
    storage.put_object(
        ObjectRef(bucket="scaffold-raw", key=DEMO_OBJECT_KEY),
        body=body,
        content_type="application/json",
    )
    # Reset put_calls so the job result can assert zero puts during staging
    storage.put_calls.clear()

    repos = RawStagingRepositories(
        object_storage=storage,
        db_writer=ScaffoldDbWriter(),
        bucket="scaffold-raw",
        seed_raws=[
            RawMetadataSeed(
                raw_metadata_id=DEMO_RAW_ID,
                object_key=DEMO_OBJECT_KEY,
                content_hash=content_hash,
                source="rakuten",
                source_api="item_search",
                import_status="raw_saved",
                batch_run_id="demo-batch",
            )
        ],
    )
    return RawStagingJob(repositories=repos)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-005 Raw ingest / Staging transform")
    parser.add_argument("--job-run-id", default="local-run")
    parser.add_argument(
        "--max-raw",
        type=int,
        default=1000,
        help="Max raw_product_metadata rows to process (default 1000).",
    )
    parser.add_argument(
        "--source-api",
        default="item_search",
        help="Comma-separated source_api filter (default item_search).",
    )
    parser.add_argument(
        "--raw-metadata-ids",
        default="",
        help="Comma-separated raw_metadata_id list (subset / re-run).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-stage even when import_status is staged/imported.",
    )
    parser.add_argument(
        "--scaffold-demo",
        action="store_true",
        help="Run in-memory scaffold demo (no real DB/Object Storage/Rakuten).",
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
        job = build_scaffold_demo_job()
        ids = _parse_csv(args.raw_metadata_ids)
        result = job.run(
            job_run_id=args.job_run_id,
            max_raw=args.max_raw,
            source_api=args.source_api,
            raw_metadata_ids=ids,
            force=args.force,
        )
        print(
            f"BATCH-005 scaffold demo status={result.status} "
            f"succeeded={len(result.succeeded_raw_ids)} "
            f"failed={len(result.failed_raw_ids)} "
            f"skipped={len(result.skipped_raw_ids)} "
            f"staging_items={result.staging_item_upsert_count} "
            f"staging_images={result.staging_item_image_upsert_count} "
            f"phases={','.join(result.completed_phases)}"
        )
        return 0 if result.status in {"succeeded", "partially_succeeded"} else 1

    import os

    settings = load_batch_settings()
    db_writer = create_db_writer(settings.database_url)
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
    print(
        f"DbWriter backend={db_writer.backend} is resolved, "
        f"storage_backend={getattr(object_storage, 'backend', 'scaffold')}, "
        "but real DB read path is not enabled yet. "
        "Use --scaffold-demo for local/CI"
        + (" (Object Storage live credentials are ready)." if storage_live else "."),
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
