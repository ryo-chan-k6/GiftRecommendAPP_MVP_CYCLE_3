"""CLI entry for BATCH-013 Feature正規化 (scaffold / GHA)."""

from __future__ import annotations

import argparse
import sys

from batch.application.feature_normalization.adapter import (
    DEFAULT_NORMALIZATION_VERSION,
    MVP_FEATURE_CODES,
    build_scaffold_adapter,
)
from batch.application.feature_normalization.job import (
    DEFAULT_MAX_ITEMS,
    DEFAULT_QUEUE_BATCH_SIZE,
    DEFAULT_SOURCE,
    FeatureNormalizationJob,
)
from batch.application.feature_normalization.models import (
    ItemRow,
    QueueRow,
    RawFeatureAxis,
)
from batch.application.feature_normalization.repositories import (
    FeatureNormalizationRepositories,
)
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

# 64 hex（BATCH-012 が付与した feature_input_hash 相当のダミー。secret ではない）
_DEMO_HASH = "b" * 64


def _parse_csv(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or raw.strip() == "":
        return None
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def build_scaffold_demo_job(
    *,
    job_run_tracker: JobRunTracker | None = None,
    phase_log_writer: PhaseLogWriter | None = None,
    error_log_writer: ErrorLogWriter | None = None,
) -> FeatureNormalizationJob:
    version = "scaffold-semantic-config-v1"
    # BATCH-012 が生成した raw 8 軸（中立 0.5〜偏り。demo 値・secret ではない）
    demo_raw = {
        "formality": 0.8,
        "safety": 0.7,
        "brand_appropriateness": 0.6,
        "emotion": 0.75,
        "novelty": 0.4,
        "intimacy": 0.55,
        "symbolic_identity": 0.5,
        "story_richness": 0.65,
    }
    raw_axes = [
        RawFeatureAxis(
            feature_code=code,
            feature_input_hash=_DEMO_HASH,
            feature_normalization_version_id=DEFAULT_NORMALIZATION_VERSION,
            raw_feature_value=demo_raw[code],
        )
        for code in MVP_FEATURE_CODES
    ]
    repos = FeatureNormalizationRepositories(
        db_writer=ScaffoldDbWriter(),
        seed_queues=[
            QueueRow(
                item_generation_queue_id="igq_demo_sem",
                item_id="it_demo_1",
                generation_type="semantic",
                queue_status="processing",
            ),
            QueueRow(
                item_generation_queue_id="igq_demo_emb",
                item_id="it_demo_2",
                generation_type="embedding",
                queue_status="queued",
            ),
        ],
        seed_items=[
            ItemRow(
                item_id="it_demo_1",
                source="rakuten",
                external_item_code="shop:demo-1",
            ),
        ],
        seed_raw_features={("it_demo_1", version): raw_axes},
        seed_config_versions={"it_demo_1": version},
        current_normalization_version_id=DEFAULT_NORMALIZATION_VERSION,
        phase_log_writer=phase_log_writer,
        error_log_writer=error_log_writer,
    )
    return FeatureNormalizationJob(
        repositories=repos,
        normalizer=build_scaffold_adapter(),
        job_run_tracker=job_run_tracker,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-013 Feature normalization")
    parser.add_argument(
        "--job-run-id",
        default="local-run",
        help="Job run id. Non --scaffold-demo Postgres tracker requires a UUID.",
    )
    parser.add_argument("--max-items", type=int, default=DEFAULT_MAX_ITEMS)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--queue-batch-size", type=int, default=DEFAULT_QUEUE_BATCH_SIZE)
    parser.add_argument("--item-ids", default="")
    parser.add_argument("--queue-ids", default="")
    parser.add_argument("--scaffold-demo", action="store_true")
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
        )
        job.repositories.bind_run(batch_run_id=args.job_run_id)
        result = job.run(
            job_run_id=args.job_run_id,
            max_items=args.max_items,
            source=args.source,
            queue_batch_size=args.queue_batch_size,
            item_ids=_parse_csv(args.item_ids),
            queue_ids=_parse_csv(args.queue_ids),
        )
        print(
            f"BATCH-013 scaffold demo status={result.status} "
            f"normalized={result.normalized_count} "
            f"skipped={result.skipped_count} "
            f"failed={result.failed_count} "
            f"normalized_updates={result.item_feature_normalized_update_count} "
            f"item_meaning_upserts={result.item_meaning_upsert_count} "
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
            "DATABASE_URL is required for non --scaffold-demo BATCH-013 "
            "(DbReader postgres backend). Use --scaffold-demo for local/CI.",
            file=sys.stderr,
        )
        return 2

    repos = FeatureNormalizationRepositories(db_writer=db_writer, db_reader=db_reader,
phase_log_writer=obs.phase_log_writer,
error_log_writer=obs.error_log_writer,
    )
    job = FeatureNormalizationJob(
        repositories=repos,
        normalizer=build_scaffold_adapter(),
        job_run_tracker=tracker,
    )
    job.repositories.bind_run(batch_run_id=args.job_run_id)
    result = job.run(
        job_run_id=args.job_run_id,
        max_items=args.max_items,
        source=args.source,
        queue_batch_size=args.queue_batch_size,
        item_ids=_parse_csv(args.item_ids),
        queue_ids=_parse_csv(args.queue_ids),
    )
    print(
        f"BATCH-013 status={result.status} "
        f"db_reader={db_reader.backend} "
        f"db_writer={db_writer.backend} "
        f"normalized={result.normalized_count} "
        f"skipped={result.skipped_count} "
        f"failed={result.failed_count} "
        f"normalized_updates={result.item_feature_normalized_update_count} "
        f"item_meaning_upserts={result.item_meaning_upsert_count} "
        f"phases={','.join(result.completed_phases)}"
    )
    return 0 if result.status in {"succeeded", "partially_succeeded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
