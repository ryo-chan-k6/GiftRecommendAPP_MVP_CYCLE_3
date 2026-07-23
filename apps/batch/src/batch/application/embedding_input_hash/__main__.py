"""CLI entry for BATCH-014 Embedding入力hash算出 (scaffold / GHA)."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

from batch.application.embedding_input_hash.job import (
    DEFAULT_MAX_ITEMS,
    DEFAULT_QUEUE_BATCH_SIZE,
    DEFAULT_SOURCE,
    EmbeddingInputHashJob,
)
from batch.application.embedding_input_hash.models import ItemRow, QueueRow
from batch.application.embedding_input_hash.repositories import (
    EmbeddingInputHashRepositories,
)
from batch.config import load_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter, create_db_writer

_NOW = datetime(2026, 7, 19, 12, 0, 0, tzinfo=UTC)


def _parse_csv(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or raw.strip() == "":
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def build_scaffold_demo_job() -> EmbeddingInputHashJob:
    repos = EmbeddingInputHashRepositories(
        db_writer=ScaffoldDbWriter(),
        seed_queues=[
            QueueRow(
                item_generation_queue_id="igq_demo_emb",
                item_id="it_demo_1",
                generation_type="embedding",
                queue_status="queued",
            ),
            QueueRow(
                item_generation_queue_id="igq_demo_sem",
                item_id="it_demo_2",
                generation_type="semantic",
                queue_status="processing",
                started_at=_NOW,
            ),
        ],
        seed_items=[
            ItemRow(
                item_id="it_demo_1",
                source="rakuten",
                external_item_code="shop:demo-1",
                item_name="Demo Gift",
                catchcopy="上品",
                item_caption="ギフト向け",
                genre_id="100371",
                genre_name="美容・コスメ",
                attributes=("hand_care",),
                tags=("季節",),
            ),
            ItemRow(
                item_id="it_demo_2",
                source="rakuten",
                external_item_code="shop:demo-2",
                item_name="Continuation Item",
            ),
        ],
    )
    return EmbeddingInputHashJob(repositories=repos)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-014 Embedding input hash")
    parser.add_argument("--job-run-id", default="local-run")
    parser.add_argument("--max-items", type=int, default=DEFAULT_MAX_ITEMS)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--queue-batch-size", type=int, default=DEFAULT_QUEUE_BATCH_SIZE)
    parser.add_argument("--item-ids", default="")
    parser.add_argument("--queue-ids", default="")
    parser.add_argument("--scaffold-demo", action="store_true")
    args = parser.parse_args(argv)

    if args.scaffold_demo:
        job = build_scaffold_demo_job()
        result = job.run(
            job_run_id=args.job_run_id,
            max_items=args.max_items,
            source=args.source,
            queue_batch_size=args.queue_batch_size,
            item_ids=_parse_csv(args.item_ids),
            queue_ids=_parse_csv(args.queue_ids),
        )
        print(
            f"BATCH-014 scaffold demo status={result.status} "
            f"hashed={result.hashed_count} "
            f"skipped={result.skipped_count} "
            f"failed={result.failed_count} "
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
