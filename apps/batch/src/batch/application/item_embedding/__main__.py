"""CLI entry for BATCH-015 Item Embedding生成 (scaffold / GHA).

Usage:
  python -m batch.application.item_embedding --job-run-id <id> [--max-items 1000]
  python -m batch.application.item_embedding --scaffold-demo
  python -m batch.application.item_embedding --scaffold-demo --live-embedding
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime

from batch.application.item_embedding.adapter import build_scaffold_adapter
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
from batch.infrastructure.db import ScaffoldDbWriter, create_db_writer
from batch.infrastructure.external_ai import (
    EmbeddingClient,
    create_embedding_client,
    resolve_live_embedding_flag,
)

_NOW = datetime(2026, 7, 20, 12, 0, 0, tzinfo=UTC)
# 64 hex（BATCH-014 handoff 相当のダミー hash。secret ではない）
_DEMO_HASH = "b" * 64


def _parse_csv(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or raw.strip() == "":
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def build_scaffold_demo_job(
    *,
    embedding_client: EmbeddingClient | None = None,
) -> ItemEmbeddingJob:
    """Build an in-memory job for local / CI smoke without real DB.

    Embedding は既定 Scaffold。``embedding_client`` 注入で live HTTP 煙が可能。
    """

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
    if embedding_client is None:
        return build_default_scaffold_job(repos)
    return ItemEmbeddingJob(
        repositories=repos,
        generator=build_scaffold_adapter(client=embedding_client),
    )


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
        help="Run in-memory scaffold demo (no real DB). Embedding live is separate.",
    )
    parser.add_argument(
        "--live-embedding",
        action="store_true",
        help=(
            "Enable real OpenAI Embeddings HTTP (requires OPENAI_API_KEY). "
            "Default off; also BATCH_EMBEDDING_LIVE. Use with --scaffold-demo for smoke."
        ),
    )
    args = parser.parse_args(argv)

    live = resolve_live_embedding_flag(
        cli_live=args.live_embedding,
        env_value=os.environ.get("BATCH_EMBEDDING_LIVE"),
    )

    if args.scaffold_demo:
        embedding_client: EmbeddingClient | None = None
        if live:
            settings = load_batch_settings()
            if not settings.openai_api_key:
                print(
                    "OPENAI_API_KEY is required for --live-embedding. "
                    "Use --scaffold-demo without --live-embedding for local/CI.",
                    file=sys.stderr,
                )
                return 2
            embedding_client = create_embedding_client(
                settings.openai_api_key,
                live=True,
            )
        job = build_scaffold_demo_job(embedding_client=embedding_client)
        result = job.run(
            job_run_id=args.job_run_id,
            max_items=args.max_items,
            source=args.source,
            queue_batch_size=args.queue_batch_size,
            item_ids=_parse_csv(args.item_ids),
            queue_ids=_parse_csv(args.queue_ids),
        )
        backend = "http" if live else "scaffold"
        print(
            f"BATCH-015 scaffold demo status={result.status} "
            f"embedding_backend={backend} "
            f"claimed={result.claimed_count} "
            f"generated={result.generated_count} "
            f"skipped={result.skipped_count} "
            f"failed={result.failed_count} "
            f"item_embedding_writes={result.item_embedding_write_count} "
            f"phases={','.join(result.completed_phases)}"
        )
        return 0 if result.status in {"succeeded", "partially_succeeded"} else 1

    settings = load_batch_settings()
    db_writer = create_db_writer(settings.database_url)
    print(
        f"DbWriter backend={db_writer.backend} is resolved, "
        "but real DB read path is not enabled yet. "
        "Use --scaffold-demo for local/CI"
        + (" (optionally with --live-embedding)." if live else "."),
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
