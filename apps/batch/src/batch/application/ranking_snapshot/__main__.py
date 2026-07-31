"""CLI entry for BATCH-002 ranking snapshot (scaffold / GHA invocation).

Usage:
  python -m batch.application.ranking_snapshot --job-run-id <id> [--genre-ids 100] [--period daily]
  python -m batch.application.ranking_snapshot --scaffold-demo
"""

from __future__ import annotations

import argparse
import sys

from batch.application.ranking_snapshot.job import (
    DEFAULT_PERIOD,
    DEFAULT_TARGET_GENRE_IDS,
    RankingSnapshotJob,
)
from batch.application.ranking_snapshot.repositories import RankingSnapshotRepositories
from batch.application.job_run import JobRunTracker, create_job_run_tracker
from batch.application.observability import (
    ApiCallLogWriter,
    ErrorLogWriter,
    PhaseLogWriter,
    create_batch_observability_writers,
)

from batch.config import load_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter, create_db_reader, create_db_writer
from batch.infrastructure.object_storage import (
    ScaffoldObjectStorageClient,
    create_object_storage_client,
    missing_live_object_storage_credentials,
    resolve_live_object_storage_flag,
)
from batch.infrastructure.rakuten import (
    RakutenRankingEntry,
    ScaffoldRakutenApiClient,
    create_rakuten_client,
    resolve_live_rakuten_flag,
)


def _parse_genre_ids(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or raw.strip() == "":
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def build_scaffold_demo_job(
    *,
    job_run_tracker: JobRunTracker | None = None,
    phase_log_writer: PhaseLogWriter | None = None,
    error_log_writer: ErrorLogWriter | None = None,
    api_call_log_writer: ApiCallLogWriter | None = None,
) -> RankingSnapshotJob:
    """Build an in-memory job for local / CI smoke without real secrets."""

    client = ScaffoldRakutenApiClient(
        ranking=(
            RakutenRankingEntry(rank=1, item_code="shop:known-1"),
            RakutenRankingEntry(rank=2, item_code="shop:unknown-2"),
        ),
        ranking_raw_responses={
            ("100", "daily", 1): {
                "lastBuildDate": "2026-07-13T12:00:00+0900",
                "genreId": "100",
                "Items": [
                    {"rank": 1, "itemCode": "shop:known-1"},
                    {"rank": 2, "itemCode": "shop:unknown-2"},
                ],
            }
        },
    )
    repos = RankingSnapshotRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=ScaffoldDbWriter(),
        bucket="scaffold-raw",
        known_item_codes={"shop:known-1"},
        phase_log_writer=phase_log_writer,
        error_log_writer=error_log_writer,
        api_call_log_writer=api_call_log_writer,
    )
    return RankingSnapshotJob(rakuten_client=client, repositories=repos,
        job_run_tracker=job_run_tracker,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-002 Rakuten ranking snapshot")
    parser.add_argument(
        "--job-run-id",
        default="local-run",
        help="Job run id. Non --scaffold-demo Postgres tracker requires a UUID.",
    )
    parser.add_argument(
        "--genre-ids",
        default="",
        help="Comma-separated genre IDs. Empty uses default fetch_plan placeholder.",
    )
    parser.add_argument(
        "--period",
        default="",
        help="Ranking period (empty = default placeholder).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=1,
        help="Max ranking pages per genre (default 1; Decision 維持。必要時のみ 2).",
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
        genre_ids = _parse_genre_ids(args.genre_ids) or DEFAULT_TARGET_GENRE_IDS
        period = args.period.strip() or DEFAULT_PERIOD
        result = job.run(
            job_run_id=args.job_run_id,
            target_genre_ids=genre_ids,
            period=period,
            max_pages=args.max_pages,
        )
        print(
            f"BATCH-002 scaffold demo status={result.status} "
            f"succeeded={len(result.succeeded_genre_ids)} "
            f"failed={len(result.failed_genre_ids)} "
            f"snapshots={result.snapshot_count} "
            f"signals={result.popularity_signal_upsert_count} "
            f"unknown={result.unknown_item_count}"
        )
        return 0 if result.status in {"succeeded", "partially_succeeded"} else 1

    import os

    settings = load_batch_settings()
    db_writer = create_db_writer(settings.database_url)
    db_reader = create_db_reader(settings.database_url)
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
    repos = RankingSnapshotRepositories(
        object_storage=object_storage,
        db_writer=db_writer,
        db_reader=db_reader,
        bucket=settings.object_storage_bucket or "scaffold-raw",
        phase_log_writer=obs.phase_log_writer,
        error_log_writer=obs.error_log_writer,
        api_call_log_writer=obs.api_call_log_writer,
    )
    job = RankingSnapshotJob(rakuten_client=rakuten, repositories=repos,
        job_run_tracker=tracker,
    )
    job.repositories.bind_run(batch_run_id=args.job_run_id)
    genre_ids = _parse_genre_ids(args.genre_ids) or DEFAULT_TARGET_GENRE_IDS
    period = args.period.strip() or DEFAULT_PERIOD
    result = job.run(
        job_run_id=args.job_run_id,
        target_genre_ids=genre_ids,
        period=period,
        max_pages=args.max_pages,
    )
    print(
        f"BATCH-002 status={result.status} "
        f"db_backend={db_writer.backend} "
        f"rakuten_backend={getattr(rakuten, 'backend', 'http')} "
        f"storage_backend={getattr(object_storage, 'backend', 'scaffold')} "
        f"succeeded={len(result.succeeded_genre_ids)} "
        f"failed={len(result.failed_genre_ids)}"
    )
    return 0 if result.status in {"succeeded", "partially_succeeded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
