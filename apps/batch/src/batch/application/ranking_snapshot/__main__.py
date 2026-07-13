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
from batch.config import load_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter
from batch.infrastructure.object_storage import ScaffoldObjectStorageClient
from batch.infrastructure.rakuten import RakutenRankingEntry, ScaffoldRakutenApiClient


def _parse_genre_ids(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or raw.strip() == "":
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def build_scaffold_demo_job() -> RankingSnapshotJob:
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
    )
    return RankingSnapshotJob(rakuten_client=client, repositories=repos)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-002 Rakuten ranking snapshot")
    parser.add_argument("--job-run-id", default="local-run")
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
        "--scaffold-demo",
        action="store_true",
        help="Run in-memory scaffold demo (no real Rakuten/DB/Object Storage).",
    )
    args = parser.parse_args(argv)

    if args.scaffold_demo:
        job = build_scaffold_demo_job()
        genre_ids = _parse_genre_ids(args.genre_ids) or DEFAULT_TARGET_GENRE_IDS
        period = args.period.strip() or DEFAULT_PERIOD
        result = job.run(
            job_run_id=args.job_run_id,
            target_genre_ids=genre_ids,
            period=period,
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

    settings = load_batch_settings()
    if not settings.rakuten_application_id:
        print(
            "RAKUTEN_APPLICATION_ID is required for non-scaffold runs. "
            "Use --scaffold-demo for local/CI.",
            file=sys.stderr,
        )
        return 2

    print(
        "Real Rakuten HTTP client is not enabled in this Task. "
        "Use --scaffold-demo, or extend infrastructure after Human Review.",
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
