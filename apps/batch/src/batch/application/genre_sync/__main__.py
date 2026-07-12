"""CLI entry for BATCH-001 genre sync (scaffold / GHA invocation).

Usage:
  python -m batch.application.genre_sync --job-run-id <id> [--genre-ids 0,100]
  python -m batch.application.genre_sync --scaffold-demo
"""

from __future__ import annotations

import argparse
import sys

from batch.application.genre_sync.job import DEFAULT_TARGET_GENRE_IDS, GenreSyncJob
from batch.application.genre_sync.repositories import GenreSyncRepositories
from batch.config import load_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter
from batch.infrastructure.object_storage import ScaffoldObjectStorageClient
from batch.infrastructure.rakuten import RakutenGenre, ScaffoldRakutenApiClient


def _parse_genre_ids(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or raw.strip() == "":
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def build_scaffold_demo_job() -> GenreSyncJob:
    """Build an in-memory job for local / CI smoke without real secrets."""

    client = ScaffoldRakutenApiClient(
        genres={
            "0": RakutenGenre(
                genre_id="0",
                genre_name="root",
                parent_genre_id=None,
                genre_level=0,
                children=("100",),
            ),
            "100": RakutenGenre(
                genre_id="100",
                genre_name="Gifts",
                parent_genre_id="0",
                genre_level=1,
                children=(),
            ),
        }
    )
    repos = GenreSyncRepositories(
        object_storage=ScaffoldObjectStorageClient(),
        db_writer=ScaffoldDbWriter(),
        bucket="scaffold-raw",
    )
    return GenreSyncJob(rakuten_client=client, repositories=repos)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-001 Rakuten genre sync")
    parser.add_argument("--job-run-id", default="local-run")
    parser.add_argument(
        "--genre-ids",
        default="",
        help="Comma-separated genre IDs. Empty uses default fetch_plan placeholder.",
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
        result = job.run(job_run_id=args.job_run_id, target_genre_ids=genre_ids)
        print(
            f"BATCH-001 scaffold demo status={result.status} "
            f"succeeded={len(result.succeeded_genre_ids)} "
            f"failed={len(result.failed_genre_ids)}"
        )
        return 0 if result.status in {"succeeded", "partially_succeeded"} else 1

    # Non-demo path: settings are validated but real HTTP client is not wired yet.
    # Production client wiring is a follow-up once secrets + HTTP transport are ready.
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
