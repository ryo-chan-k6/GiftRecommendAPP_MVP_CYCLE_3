"""CLI entry for BATCH-016 分布メトリクス集計 (scaffold / GHA).

Usage:
  python -m batch.application.distribution_metrics --scaffold-demo
  python -m batch.application.distribution_metrics --job-run-id <id>  # exit 3 (real DB off)
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

from batch.application.distribution_metrics.job import (
    DEFAULT_SEMANTIC_CONFIG_VERSION,
    DistributionMetricsJob,
)
from batch.application.distribution_metrics.models import (
    ItemEmbeddingRow,
    ItemFeatureRow,
    ItemMeaningRow,
    UserMeaningRow,
)
from batch.application.distribution_metrics.repositories import (
    DistributionMetricsRepositories,
)
from batch.config import load_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter, create_db_writer

_DEMO_NORM_VERSION = "scaffold-feature-normalization-v1"
_DEMO_MODEL_VERSION = "scaffold-embedding-model-v1"
# 64 hex（handoff 相当のダミー。secret ではない）
_DEMO_HASH = "b" * 64

_MVP_CODES = (
    "formality",
    "safety",
    "brand_appropriateness",
    "emotion",
    "novelty",
    "intimacy",
    "symbolic_identity",
    "story_richness",
)

_DEMO_RAW = {
    "formality": 0.8,
    "safety": 0.7,
    "brand_appropriateness": 0.6,
    "emotion": 0.75,
    "novelty": 0.4,
    "intimacy": 0.55,
    "symbolic_identity": 0.5,
    "story_richness": 0.65,
}
_DEMO_NORM = {
    "formality": 0.82,
    "safety": 0.71,
    "brand_appropriateness": 0.62,
    "emotion": 0.77,
    "novelty": 0.42,
    "intimacy": 0.56,
    "symbolic_identity": 0.51,
    "story_richness": 0.66,
}


def _parse_bool(raw: str | None, *, default: bool = False) -> bool:
    if raw is None or raw.strip() == "":
        return default
    lowered = raw.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise SystemExit(f"invalid boolean value: {raw!r}")


def build_scaffold_demo_job() -> DistributionMetricsJob:
    """Build an in-memory job for local / CI smoke without real secrets / DB."""

    version = DEFAULT_SEMANTIC_CONFIG_VERSION
    features: list[ItemFeatureRow] = []
    for item_id, scale in (("it_demo_1", 1.0), ("it_demo_2", 0.9)):
        for code in _MVP_CODES:
            features.append(
                ItemFeatureRow(
                    item_id=item_id,
                    semantic_config_version_id=version,
                    feature_code=code,
                    raw_feature_value=_DEMO_RAW[code] * scale,
                    normalized_feature_value=_DEMO_NORM[code] * scale,
                    feature_normalization_version_id=_DEMO_NORM_VERSION,
                )
            )
    meanings = [
        ItemMeaningRow(
            item_id="it_demo_1",
            semantic_config_version_id=version,
            item_social=0.7,
            item_symbolic=0.55,
            feature_normalization_version_id=_DEMO_NORM_VERSION,
        ),
        ItemMeaningRow(
            item_id="it_demo_2",
            semantic_config_version_id=version,
            item_social=0.65,
            item_symbolic=0.5,
            feature_normalization_version_id=_DEMO_NORM_VERSION,
        ),
    ]
    user_meanings = [
        UserMeaningRow(
            user_id="usr_demo_1",
            semantic_config_version_id=version,
            user_social=0.6,
            user_symbolic=0.45,
            lambda_ctx=0.5,
            feature_normalization_version_id=_DEMO_NORM_VERSION,
        ),
    ]
    embeddings = [
        ItemEmbeddingRow(
            item_id="it_demo_1",
            model_version_id=_DEMO_MODEL_VERSION,
            embedding_input_hash=_DEMO_HASH,
        ),
    ]
    repos = DistributionMetricsRepositories(
        db_writer=ScaffoldDbWriter(),
        seed_item_features=features,
        seed_item_meanings=meanings,
        seed_user_meanings=user_meanings,
        seed_item_embeddings=embeddings,
    )
    return DistributionMetricsJob(repositories=repos)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-016 Distribution metrics aggregation")
    parser.add_argument("--job-run-id", default="local-run")
    parser.add_argument("--trigger-mode", default="dispatch")
    parser.add_argument("--semantic-config-version-id", default="")
    parser.add_argument("--aggregation-scope", default="")
    parser.add_argument("--include-item-embedding", default="")
    parser.add_argument("--include-user-meaning", default="")
    parser.add_argument(
        "--scaffold-demo",
        action="store_true",
        help="Run in-memory scaffold demo (no real DB).",
    )
    args = parser.parse_args(argv)

    if args.scaffold_demo:
        settings = load_batch_settings()
        include_embedding = _parse_bool(
            args.include_item_embedding or None,
            default=bool(settings.batch_distribution_metrics_include_item_embedding),
        )
        include_user = _parse_bool(
            args.include_user_meaning or None,
            default=bool(settings.batch_distribution_metrics_include_user_meaning),
        )
        scope_override = (
            args.aggregation_scope.strip()
            or settings.batch_distribution_metrics_aggregation_scope
            or None
        )
        version = (
            args.semantic_config_version_id.strip()
            or settings.batch_distribution_metrics_semantic_config_version_id
            or DEFAULT_SEMANTIC_CONFIG_VERSION
        )
        job = build_scaffold_demo_job()
        result = job.run(
            job_run_id=args.job_run_id,
            trigger_mode=args.trigger_mode,
            semantic_config_version_id=version,
            aggregation_scope=scope_override,
            include_item_embedding=include_embedding,
            include_user_meaning=include_user,
            now=datetime.now(UTC),
        )
        print(
            f"BATCH-016 scaffold demo status={result.status} "
            f"scope={result.aggregation_scope} "
            f"feature_upserts={result.feature_metric_upsert_count} "
            f"meaning_upserts={result.meaning_metric_upsert_count} "
            f"normalization_upserts={result.normalization_metric_upsert_count} "
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
