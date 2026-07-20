"""CLI entry for BATCH-015 Item Embedding生成 (scaffold / GHA).

Usage:
  python -m batch.application.item_embedding --job-run-id <id> [--max-items 1000]
  python -m batch.application.item_embedding --scaffold-demo
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

from batch.application.item_embedding.job import (
    DEFAULT_MAX_ITEMS,
    DEFAULT_QUEUE_BATCH_SIZE,
    DEFAULT_SOURCE,
    ItemEmbeddingJob,
    build_default_scaffold_job,
)
from batch.application.item_embedding.models import (
    EmbeddingHashHandoff,
    ItemRow,
    QueueRow,
)
from batch.application.item_embedding.repositories import (
    DEFAULT_EMBEDDING_MODEL_VERSION,
    ItemEmbeddingRepositories,
)
from batch.config import load_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter

_NOW = datetime(2026, 7, 20, 12, 0, 0, tzinfo=UTC)
# 64 hex（BATCH-014 handoff 相当のダミー hash。secret ではない）
_DEMO_HASH = "b" * 64


def _parse_csv(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or raw.strip() == "":
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def build_scaffold_demo_job() -> ItemEmbeddingJob:
    """Build an in-memory job for local / CI smoke without real secrets / DB / OpenAI."""

    context = {
        "item_id": "it_demo_1",
        "item_name": "Demo Gift Embedding",
        "catchcopy": "上品",
        "item_caption": "ギフト向け",
        "genre_id": "100371",
        "genre_name": "美容・コスメ",
        "attributes": ["hand_care"],
        "tags": ["季節"],
        "embedding_source_type": "item_text_context",
        "embedding_source_version": "scaffold-embedding-source-v1",
    }
    repos = ItemEmbeddingRepositories(
        db_writer=ScaffoldDbWriter(),
        seed_queues=[
            QueueRow(
                item_generation_queue_id="igq_demo_emb",
                item_id="it_demo_1",
                generation_type="embedding",
                queue_status="processing",
                started_at=_NOW,
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
            ),
            ItemRow(
                item_id="it_demo_2",
                source="rakuten",
                external_item_code="shop:demo-2",
            ),
        ],
        seed_handoffs=[
            EmbeddingHashHandoff(
                item_id="it_demo_1",
                item_generation_queue_id="igq_demo_emb",
                model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION,
                embedding_source_type="item_text_context",
                embedding_source_version="scaffold-embedding-source-v1",
                embedding_input_hash=_DEMO_HASH,
                item_text_context=context,
            ),
            EmbeddingHashHandoff(
                item_id="it_demo_2",
                item_generation_queue_id="igq_demo_sem",
                model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION,
                embedding_source_type="item_text_context",
                embedding_source_version="scaffold-embedding-source-v1",
                embedding_input_hash="c" * 64,
                item_text_context={
                    **context,
                    "item_id": "it_demo_2",
                    "item_name": "Continuation Semantic",
                },
            ),
        ],
    )
    return build_default_scaffold_job(repos)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-015 Item Embedding generation")
    parser.add_argument("--job-run-id", default="local-run")
    parser.add_argument("--max-items", type=int, default=DEFAULT_MAX_ITEMS)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--queue-batch-size", type=int, default=DEFAULT_QUEUE_BATCH_SIZE)
    parser.add_argument("--item-ids", default="")
    parser.add_argument("--queue-ids", default="")
    parser.add_argument(
        "--scaffold-demo",
        action="store_true",
        help="Run in-memory scaffold demo (no real DB / OpenAI).",
    )
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
            f"BATCH-015 scaffold demo status={result.status} "
            f"claimed={result.claimed_count} "
            f"generated={result.generated_count} "
            f"skipped={result.skipped_count} "
            f"failed={result.failed_count} "
            f"item_embedding_writes={result.item_embedding_write_count} "
            f"phases={','.join(result.completed_phases)}"
        )
        return 0 if result.status in {"succeeded", "partially_succeeded"} else 1

    settings = load_batch_settings()
    _ = settings  # real wiring is out of this Task (scaffold-first)
    print(
        "Real DB client is not enabled in this Task. "
        "Use --scaffold-demo for local/CI.",
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
