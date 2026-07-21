"""CLI entry for BATCH-018 Offline Evaluation (scaffold / GHA).

Usage:
  python -m batch.application.offline_evaluation --scaffold-demo
  python -m batch.application.offline_evaluation --job-run-id <id>  # exit 3 (real DB off)
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

from batch.application.offline_evaluation.job import OfflineEvaluationJob
from batch.application.offline_evaluation.models import (
    EvaluationCaseRow,
    EvaluationDatasetRow,
)
from batch.application.offline_evaluation.repositories import (
    OfflineEvaluationRepositories,
)
from batch.config import load_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter
from batch.infrastructure.reco_client import MockRecoEvaluationClient

_DEMO_DATASET_ID = "ds-scaffold-018"
_DEMO_DATASET_NAME = "scaffold_offline_eval"
_DEMO_DATASET_VERSION = "v1"


def build_scaffold_demo_job() -> OfflineEvaluationJob:
    """Build an in-memory job for local / CI smoke without real secrets / DB."""

    datasets = [
        EvaluationDatasetRow(
            evaluation_dataset_id=_DEMO_DATASET_ID,
            dataset_name=_DEMO_DATASET_NAME,
            dataset_version=_DEMO_DATASET_VERSION,
            is_active=True,
        )
    ]
    cases = [
        EvaluationCaseRow(
            evaluation_case_id="case-scaffold-001",
            evaluation_dataset_id=_DEMO_DATASET_ID,
            case_label="case_001",
            input_condition_json={"relationship": "friend", "occasion": "birthday"},
            expected_result_json={
                "golden_item_ids": ["item-a", "item-b", "item-c"],
            },
            is_active=True,
        ),
        EvaluationCaseRow(
            evaluation_case_id="case-scaffold-002",
            evaluation_dataset_id=_DEMO_DATASET_ID,
            case_label="case_002",
            input_condition_json={"relationship": "family", "occasion": "thanks"},
            expected_result_json={
                "golden_item_ids": ["item-x", "item-y"],
            },
            is_active=True,
        ),
    ]
    repos = OfflineEvaluationRepositories(
        db_writer=ScaffoldDbWriter(),
        seed_datasets=datasets,
        seed_cases=cases,
    )
    return OfflineEvaluationJob(
        repositories=repos,
        reco_client=MockRecoEvaluationClient(),
    )


def _parse_optional_int(raw: str | None) -> int | None:
    if raw is None or raw.strip() == "":
        return None
    try:
        value = int(raw.strip())
    except ValueError as exc:
        raise SystemExit(f"invalid integer: {raw!r}") from exc
    if value <= 0:
        raise SystemExit(f"must be positive: {raw!r}")
    return value


def _parse_bool(raw: str | None, *, default: bool = False) -> bool:
    if raw is None or raw.strip() == "":
        return default
    lowered = raw.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise SystemExit(f"invalid boolean value: {raw!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BATCH-018 Offline Evaluation")
    parser.add_argument("--job-run-id", default="local-run")
    parser.add_argument("--evaluation-dataset-id", default="")
    parser.add_argument("--dataset-name", default="")
    parser.add_argument("--dataset-version", default="")
    parser.add_argument("--max-cases", default="")
    parser.add_argument("--dry-run", default="")
    parser.add_argument(
        "--scaffold-demo",
        action="store_true",
        help="Run in-memory scaffold demo (no real DB / no HTTP).",
    )
    args = parser.parse_args(argv)

    if args.scaffold_demo:
        settings = load_batch_settings()
        dataset_id = (
            args.evaluation_dataset_id.strip()
            or settings.batch_offline_evaluation_dataset_id
            or _DEMO_DATASET_ID
        )
        dataset_name = (
            args.dataset_name.strip()
            or settings.batch_offline_evaluation_dataset_name
            or None
        )
        dataset_version = (
            args.dataset_version.strip()
            or settings.batch_offline_evaluation_dataset_version
            or None
        )
        max_cases = _parse_optional_int(
            args.max_cases or None
        ) or settings.batch_offline_evaluation_max_cases
        dry_run = _parse_bool(
            args.dry_run or None,
            default=bool(settings.batch_offline_evaluation_dry_run),
        )
        job = build_scaffold_demo_job()
        result = job.run(
            job_run_id=args.job_run_id,
            evaluation_dataset_id=dataset_id,
            dataset_name=dataset_name,
            dataset_version=dataset_version,
            max_cases=max_cases,
            dry_run=dry_run,
            now=datetime.now(UTC),
        )
        print(
            f"BATCH-018 scaffold demo status={result.status} "
            f"dataset={result.evaluation_dataset_id} "
            f"run={result.evaluation_run_id} "
            f"cases={result.cases_evaluated} "
            f"results={result.results_inserted} "
            f"metrics={result.metrics_inserted} "
            f"phases={','.join(result.completed_phases)}"
        )
        return 0 if result.status in {"succeeded", "partially_succeeded"} else 1

    settings = load_batch_settings()
    _ = settings
    print(
        "Real DB client is not enabled in this Task. Use --scaffold-demo for local/CI.",
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
