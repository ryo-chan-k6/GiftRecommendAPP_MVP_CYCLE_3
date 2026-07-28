"""CLI entry for BATCH-005 Raw取込・Staging変換 (scaffold / GHA invocation).

Usage:
  python -m batch.application.raw_staging --job-run-id <id> [--max-raw 100]
  python -m batch.application.raw_staging --scaffold-demo
  python -m batch.application.raw_staging \\
    --job-run-id <leaf-uuid> --batch-run-id <pipeline-uuid>
  python -m batch.application.raw_staging --live-object-storage  # + DATABASE_URL / OBJECT_STORAGE_*
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from batch.application.raw_staging.hashing import content_hash_for_bytes
from batch.application.raw_staging.job import RawStagingJob
from batch.application.raw_staging.models import RawMetadataSeed
from batch.application.raw_staging.repositories import RawStagingRepositories
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


def _resolve_business_run_id(*, job_run_id: str, batch_run_id: str) -> str:
    """Shared pipeline UUID for obs bind. Falls back to job_run_id."""

    return batch_run_id.strip() or job_run_id


def build_scaffold_demo_job(
    *,
    job_run_tracker: JobRunTracker | None = None,
    phase_log_writer: PhaseLogWriter | None = None,
    error_log_writer: ErrorLogWriter | None = None,
) -> RawStagingJob:
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
        phase_log_writer=phase_log_writer,
        error_log_writer=error_log_writer,
    )
    return RawStagingJob(repositories=repos,
job_run_tracker=job_run_tracker,
    )


def _print_run_summary(result: object) -> None:
    print(
        f"BATCH-005 status={getattr(result, 'status', '?')} "
        f"succeeded={len(getattr(result, 'succeeded_raw_ids', ()))} "
        f"failed={len(getattr(result, 'failed_raw_ids', ()))} "
        f"skipped={len(getattr(result, 'skipped_raw_ids', ()))} "
        f"staging_items={getattr(result, 'staging_item_upsert_count', 0)} "
        f"staging_images={getattr(result, 'staging_item_image_upsert_count', 0)} "
        f"phases={','.join(getattr(result, 'completed_phases', ()))}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-005 Raw ingest / Staging transform")
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
            "共有 pipeline batch_run_id（obs bind）。"
            "未指定時は --job-run-id にフォールバック。"
        ),
    )
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
            "DATABASE_URL is required for non --scaffold-demo BATCH-005 "
            "(DbReader postgres backend). Use --scaffold-demo for local/CI.",
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
        if not settings.object_storage_bucket:
            print(
                "OBJECT_STORAGE_BUCKET is required when --live-object-storage "
                "/ BATCH_OBJECT_STORAGE_LIVE is enabled.",
                file=sys.stderr,
            )
            return 2

    object_storage = create_object_storage_client(
        settings.object_storage_access_key,
        settings.object_storage_secret_key,
        endpoint=settings.object_storage_endpoint,
        live=storage_live,
    )
    bucket = settings.object_storage_bucket or "scaffold-raw"
    repos = RawStagingRepositories(
        object_storage=object_storage,
        db_writer=db_writer,
        db_reader=db_reader,
        bucket=bucket,
        phase_log_writer=obs.phase_log_writer,
        error_log_writer=obs.error_log_writer,
    )
    job = RawStagingJob(repositories=repos,
job_run_tracker=tracker,
    )
    job.repositories.bind_run(batch_run_id=business_run_id)
    ids = _parse_csv(args.raw_metadata_ids)
    result = job.run(
        job_run_id=args.job_run_id,
        max_raw=args.max_raw,
        source_api=args.source_api,
        raw_metadata_ids=ids,
        force=args.force,
    )
    _print_run_summary(result)
    print(
        f"db_reader={db_reader.backend} db_writer={db_writer.backend} "
        f"storage_backend={getattr(object_storage, 'backend', 'unknown')}"
    )
    return 0 if result.status in {"succeeded", "partially_succeeded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
