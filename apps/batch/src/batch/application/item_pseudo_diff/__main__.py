"""CLI entry for BATCH-003 item pseudo-diff (scaffold / GHA invocation).

Usage:
  python -m batch.application.item_pseudo_diff --job-run-id <id> [--genre-ids 100]
  python -m batch.application.item_pseudo_diff --scaffold-demo
  python -m batch.application.item_pseudo_diff \\
    --job-run-id <leaf-uuid> --batch-run-id <pipeline-uuid> --live-rakuten
"""

from __future__ import annotations

import argparse
import sys

from batch.application.item_pseudo_diff.job import (
    DEFAULT_CURSORS_PER_RUN,
    DEFAULT_HITS,
    DEFAULT_PAGES_PER_RUN,
    DEFAULT_TARGET_GENRE_IDS,
    ItemPseudoDiffJob,
)
from batch.application.item_pseudo_diff.models import FetchCursorRow
from batch.application.item_pseudo_diff.repositories import ItemPseudoDiffRepositories
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
    RakutenItem,
    ScaffoldRakutenApiClient,
    create_rakuten_client,
    resolve_live_rakuten_flag,
)


def _parse_csv(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or raw.strip() == "":
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _resolve_business_run_id(*, job_run_id: str, batch_run_id: str) -> str:
    """Shared pipeline UUID for obs / raw object key. Falls back to job_run_id."""

    return batch_run_id.strip() or job_run_id


def _resolve_pages_per_run(args: argparse.Namespace) -> int:
    """Prefer --pages-per-run; --max-pages is a compatibility alias."""

    if args.max_pages is not None and args.pages_per_run == DEFAULT_PAGES_PER_RUN:
        return max(1, int(args.max_pages))
    return max(1, int(args.pages_per_run))


def _build_scaffold_rakuten_client() -> ScaffoldRakutenApiClient:
    """In-memory Rakuten responses for CI / GHA（登録 egress IP 外での live 禁止に合わせる）。

    Raw は BATCH-005 staging 検証（itemUrl / itemPrice 等）を通る最小形にする。
    """

    def _item(
        *,
        code: str,
        name: str,
        price: int = 1980,
    ) -> dict[str, object]:
        return {
            "Item": {
                "itemCode": code,
                "itemName": name,
                "itemCaption": f"Caption for {name}",
                "catchcopy": "Demo catch",
                "itemPrice": price,
                "itemUrl": f"https://item.example/{code}",
                "genreId": 100,
                "shopCode": code.split(":", 1)[0],
                "availability": 1,
                "reviewAverage": 4.0,
                "reviewCount": 1,
                "mediumImageUrls": [{"imageUrl": f"https://img.example/medium/{code}.jpg"}],
                "smallImageUrls": [{"imageUrl": f"https://img.example/small/{code}.jpg"}],
            }
        }

    return ScaffoldRakutenApiClient(
        items=(
            RakutenItem(item_code="shop:demo-1", item_name="Demo Item 1"),
            RakutenItem(item_code="shop:demo-2", item_name="Demo Item 2"),
        ),
        item_search_raw_responses={
            ("genre", "100", 1): {
                "Items": [
                    _item(code="shop:demo-1", name="Demo Item 1", price=1980),
                    _item(code="shop:demo-2", name="Demo Item 2", price=2980),
                ]
            },
            ("update_sort", "*", 1): {
                "Items": [
                    _item(code="shop:demo-1", name="Demo Item 1", price=1980),
                ]
            },
            ("ranking_supplement", "shop:unknown-rank", 1): {
                "Items": [
                    _item(
                        code="shop:unknown-rank",
                        name="From Ranking Supplement",
                        price=1500,
                    ),
                ]
            },
        },
    )


def build_scaffold_demo_job(
    *,
    job_run_tracker: JobRunTracker | None = None,
    phase_log_writer: PhaseLogWriter | None = None,
    error_log_writer: ErrorLogWriter | None = None,
    api_call_log_writer: ApiCallLogWriter | None = None,
) -> ItemPseudoDiffJob:
    """Build an in-memory job for local / CI smoke without real secrets."""

    client = _build_scaffold_rakuten_client()
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
        phase_log_writer=phase_log_writer,
        error_log_writer=error_log_writer,
        api_call_log_writer=api_call_log_writer,
    )
    return ItemPseudoDiffJob(rakuten_client=client, repositories=repos,
job_run_tracker=job_run_tracker,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-003 Rakuten item pseudo-diff")
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
            "共有 pipeline batch_run_id（obs bind / raw object key）。"
            "未指定時は --job-run-id にフォールバック。"
        ),
    )
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
        "--pages-per-run",
        type=int,
        default=DEFAULT_PAGES_PER_RUN,
        help=(
            "Run予算: 1 Run で進める最大ページ数（カタログ深さ打ち切りではない）。"
            f" 既定={DEFAULT_PAGES_PER_RUN}（smoke）。通常継続は 60。"
        ),
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="互換 alias（--pages-per-run と同義）。両方指定時は --pages-per-run 優先。",
    )
    parser.add_argument(
        "--cursors-per-run",
        type=int,
        default=DEFAULT_CURSORS_PER_RUN,
        help=f"Run予算: 1 Run で着手する最大 cursor 数。既定={DEFAULT_CURSORS_PER_RUN}。",
    )
    parser.add_argument(
        "--wall-clock-seconds",
        type=int,
        default=0,
        help="Run予算: wall-clock 上限秒（0=無効）。通常継続の目安は 2700（45分）。",
    )
    parser.add_argument(
        "--hits",
        type=int,
        default=DEFAULT_HITS,
        help=f"ItemSearch hits（1〜30）。既定={DEFAULT_HITS}。",
    )
    parser.add_argument(
        "--max-qps",
        type=float,
        default=1.0,
        help=(
            "楽天 live 時の安全側 QPS（BATCH-003 既定=1）。"
            "常用 QPS=2 の Decision は変更しない。scaffold 時は無視。"
        ),
    )
    parser.add_argument(
        "--no-update-sort",
        action="store_true",
        help=(
            "update_sort ルートを本 Run の計画から除外する。"
            "MVP 初回 smoke / fetch_plan 承認（初期は update_sort=off）向け。"
        ),
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
            api_call_log_writer=obs.api_call_log_writer,
        )
        job.repositories.bind_run(batch_run_id=business_run_id)
        genre_ids = _parse_csv(args.genre_ids) or DEFAULT_TARGET_GENRE_IDS
        keywords = _parse_csv(args.keywords)
        pages_per_run = _resolve_pages_per_run(args)
        result = job.run(
            job_run_id=args.job_run_id,
            batch_run_id=business_run_id,
            target_genre_ids=genre_ids,
            keywords=keywords,
            pages_per_run=pages_per_run,
            cursors_per_run=args.cursors_per_run,
            wall_clock_seconds=args.wall_clock_seconds or None,
            hits=args.hits,
            include_update_sort=not args.no_update_sort,
        )
        print(
            f"BATCH-003 scaffold demo status={result.status} "
            f"succeeded={len(result.succeeded_cursor_ids)} "
            f"failed={len(result.failed_cursor_ids)} "
            f"pages={result.pages_fetched} "
            f"budget_stopped={result.run_budget_stopped} "
            f"raw_saves={result.raw_save_success_count} "
            f"candidates={result.candidate_item_code_count} "
            f"supplement={result.ranking_supplement_consumed_count}"
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
    # 案 A: GHA 等では楽天 HTTP せず Scaffold。DB / Object Storage は live 可。
    # 楽天 live は登録 egress IP の local のみ（PoC / Human 決定）。
    if live:
        if not settings.rakuten_application_id or not settings.rakuten_access_key:
            print(
                "RAKUTEN_APPLICATION_ID and RAKUTEN_ACCESS_KEY are required for --live-rakuten. "
                "Omit --live-rakuten to use scaffold Rakuten with live DB/Storage.",
                file=sys.stderr,
            )
            return 2
        rakuten = create_rakuten_client(
            settings.rakuten_application_id,
            settings.rakuten_access_key,
            live=True,
            max_qps=args.max_qps,
        )
    else:
        rakuten = _build_scaffold_rakuten_client()

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

    repos = ItemPseudoDiffRepositories(
        object_storage=object_storage,
        db_writer=db_writer,
        db_reader=db_reader,
        bucket=settings.object_storage_bucket or "scaffold-raw",
        phase_log_writer=obs.phase_log_writer,
        error_log_writer=obs.error_log_writer,
        api_call_log_writer=obs.api_call_log_writer,
    )
    job = ItemPseudoDiffJob(
        rakuten_client=rakuten,
        repositories=repos,
        job_run_tracker=tracker,
    )
    job.repositories.bind_run(batch_run_id=business_run_id)
    genre_ids = _parse_csv(args.genre_ids) or DEFAULT_TARGET_GENRE_IDS
    keywords = _parse_csv(args.keywords)
    pages_per_run = _resolve_pages_per_run(args)
    result = job.run(
        job_run_id=args.job_run_id,
        batch_run_id=business_run_id,
        target_genre_ids=genre_ids,
        keywords=keywords,
        pages_per_run=pages_per_run,
        cursors_per_run=args.cursors_per_run,
        wall_clock_seconds=args.wall_clock_seconds or None,
        hits=args.hits,
        include_update_sort=not args.no_update_sort,
    )
    error_codes = ",".join(result.error_codes) if result.error_codes else "-"
    print(
        f"BATCH-003 status={result.status} "
        f"db_backend={db_writer.backend} "
        f"rakuten_backend={getattr(rakuten, 'backend', 'http')} "
        f"storage_backend={getattr(object_storage, 'backend', 'scaffold')} "
        f"pages={result.pages_fetched} "
        f"budget_stopped={result.run_budget_stopped} "
        f"succeeded={len(result.succeeded_cursor_ids)} "
        f"failed={len(result.failed_cursor_ids)} "
        f"error_codes={error_codes}"
    )
    for entry in repos.error_logs:
        code = entry.get("code", "")
        summary = entry.get("summary", "")
        print(f"BATCH-003 error code={code} summary={summary}", file=sys.stderr)
    return 0 if result.status in {"succeeded", "partially_succeeded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
