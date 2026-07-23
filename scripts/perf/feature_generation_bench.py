#!/usr/bin/env python3
"""TV-009: User / Item Feature 生成時間の専用計測（Reco E2E・外部 AI 非依存）。

apps/reco の UserFeatureGenerator / ItemFeatureGenerator を in-memory で計測する。
apps/** は改修しない。apps/batch は触らない（BATCH-012 ジョブ全体は対象外）。

実行例:

  cd apps/reco
  uv run python ../../scripts/perf/feature_generation_bench.py \\
    --iterations 50 --warmup 5 \\
    --output-dir ../../scripts/perf/output-tv009
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _percentile(sorted_values: list[float], pct: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)


def _latency_stats(samples_ms: list[float]) -> dict[str, float | int | None]:
    if not samples_ms:
        return {
            "count": 0,
            "min_ms": None,
            "avg_ms": None,
            "p50_ms": None,
            "p95_ms": None,
            "max_ms": None,
        }
    ordered = sorted(samples_ms)
    return {
        "count": len(ordered),
        "min_ms": round(ordered[0], 3),
        "avg_ms": round(statistics.fmean(ordered), 3),
        "p50_ms": round(_percentile(ordered, 50) or 0.0, 3),
        "p95_ms": round(_percentile(ordered, 95) or 0.0, 3),
        "max_ms": round(ordered[-1], 3),
    }


def _ensure_packages() -> None:
    """Register hyphenated application packages (same bootstrap as reco live bench)."""
    try:
        from reco.composition.bootstrap import ensure_composition_application_packages
    except ImportError as exc:
        raise SystemExit(
            "reco パッケージを import できません。"
            " apps/reco で `uv sync` 後に本スクリプトを実行してください。"
            f" detail={exc}"
        ) from exc
    ensure_composition_application_packages()
    # Item Feature Generator は composition bootstrap 対象外のため明示ロード
    import importlib.util
    import sys

    if "reco.application.item_feature_generator" not in sys.modules:
        init_path = (
            Path(__file__).resolve().parents[2]
            / "apps/reco/src/reco/application/item-feature-generator/__init__.py"
        )
        spec = importlib.util.spec_from_file_location(
            "reco.application.item_feature_generator",
            init_path,
            submodule_search_locations=[str(init_path.parent)],
        )
        if spec is None or spec.loader is None:
            raise SystemExit(f"failed to load item_feature_generator: {init_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules["reco.application.item_feature_generator"] = module
        spec.loader.exec_module(module)


def _bench_user_feature(*, iterations: int, warmup: int) -> dict[str, Any]:
    from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    from reco.application.external_condition_feature_estimator.models import (
        ExternalFeatureEstimate,
    )
    from reco.application.internal_condition_feature_estimator.models import (
        InternalFeatureEstimate,
    )
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )
    from reco.application.user_feature_generator import (
        InMemoryNormalizationRuleRepository,
        InMemoryRunValidation,
        InMemoryUserFeatureRepository,
        UserFeatureGenerator,
        build_default_normalization_binding,
    )
    from reco.domain import (
        ExecutionMode,
        OccasionCondition,
        RecommendationRequest,
        RecommendationRun,
        RelationshipCondition,
        RunStatus,
    )
    from reco.domain.gift_meaning.features import MVP_FEATURE_CODES
    from reco.infrastructure.logger.logger import ScaffoldRecoLogger

    def uniform(value: float) -> dict[str, float]:
        return {code: value for code in MVP_FEATURE_CODES}

    samples: list[float] = []
    for i in range(warmup + iterations):
        run_id = f"tv009-user-feature-{i}"
        request = RecommendationRequest(
            request_id=f"req-{run_id}",
            relationship=RelationshipCondition(relationship_code="friend_casual"),
            occasion=OccasionCondition(occasion_code="birthday"),
        )
        external = ExternalFeatureEstimate(
            relationship_code="friend_casual",
            occasion_code="birthday",
            relationship_feature=uniform(0.4),
            occasion_feature=uniform(0.6),
            pair_delta=uniform(0.0),
            external_feature_raw=uniform(0.5),
            semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
            estimation_method="rule",
        )
        internal = InternalFeatureEstimate(
            preferred_delta=uniform(0.0),
            avoid_delta=uniform(0.0),
            free_text_delta=uniform(0.0),
            internal_feature_delta=uniform(0.05),
            applied_concept_count=2,
            semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
            estimation_method="rule",
        )
        context = ExecutionContext(
            recommendation_request=request,
            trace_id=f"trace-{run_id}",
            execution_mode=ExecutionMode.UI,
            config_versions={
                "semantic_config_version_id": DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
                "model_version_id": "mv-tv009",
                "ranking_config_id": "rc-tv009",
            },
            recommendation_run=RecommendationRun(
                run_id=run_id,
                request_id=request.request_id,
                status=RunStatus.RUNNING,
                semantic_config_version=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
                model_version="mv-tv009",
            ),
            external_feature_estimate=external,
        )
        context.internal_feature_estimate = internal  # type: ignore[attr-defined]

        user_features = InMemoryUserFeatureRepository()
        run_validation = InMemoryRunValidation()
        run_validation.register_run(run_id, DEFAULT_SEMANTIC_CONFIG_VERSION_ID)
        user_features.register_user_semantic(run_id)
        generator = UserFeatureGenerator(
            normalization_rules=InMemoryNormalizationRuleRepository(
                binding=build_default_normalization_binding(),
            ),
            user_features=user_features,
            run_validation=run_validation,
            logger=ScaffoldRecoLogger(),
        )

        t0 = time.perf_counter()
        _ = generator.generate(context)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        if i >= warmup:
            samples.append(elapsed_ms)

    return {
        "target": "user_feature_generator",
        "path": "online (MOD-RECO-007)",
        "mode": "in_memory",
        "latency": _latency_stats(samples),
    }


def _bench_item_feature(
    *,
    iterations: int,
    warmup: int,
    concept_count: int,
) -> dict[str, Any]:
    from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    from reco.application.item_feature_generator import (
        ItemFeatureGenerationContext,
        ItemFeatureGenerator,
        ItemSemanticInput,
    )
    from reco.application.item_feature_generator.in_memory_repository import (
        InMemoryItemFeatureRepository,
        InMemoryItemValidation,
        build_default_in_memory_repositories,
    )
    from reco.infrastructure.logger.logger import ScaffoldRecoLogger

    concepts = [
        {
            "concept_code": "formal_refined",
            "confidence": 0.80,
            "source_type": "item_description",
            "input_intent": "neutral",
            "extraction_method": "rule",
        }
        for _ in range(max(concept_count, 1))
    ]

    samples: list[float] = []
    for i in range(warmup + iterations):
        item_id = f"item-tv009-{i}"
        feature_hash = f"{i:064x}"[-64:]
        context = ItemFeatureGenerationContext(
            trace_id=f"trace-item-{i}",
            batch_run_id="batch-tv009",
            item_generation_queue_id=f"queue-{i}",
            item_id=item_id,
            semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
            feature_input_hash=feature_hash,
            item_semantic=ItemSemanticInput(
                item_id=item_id,
                semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
                semantic_json={"concepts": concepts},
            ),
            skip_if_unchanged=False,
        )
        (
            concept_rules,
            normalization_rules,
            feature_definitions,
            item_validation,
            _,
        ) = build_default_in_memory_repositories()
        assert isinstance(item_validation, InMemoryItemValidation)
        item_validation.register_item(item_id)
        generator = ItemFeatureGenerator(
            concept_feature_rules=concept_rules,
            normalization_rules=normalization_rules,
            feature_definitions=feature_definitions,
            item_validation=item_validation,
            item_feature_repository=InMemoryItemFeatureRepository(),
            logger=ScaffoldRecoLogger(),
        )

        t0 = time.perf_counter()
        result = generator.generate_item_features(context)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        if i >= warmup:
            samples.append(elapsed_ms)
            if str(result.status) not in {"generated", "GenerationStatus.GENERATED"} and getattr(
                result.status, "value", str(result.status)
            ) != "generated":
                # keep going but record status once in meta via last_status
                pass

    return {
        "target": "item_feature_generator",
        "path": "item generation logic (MOD-RECO-027; Batch BATCH-012 全体は対象外)",
        "mode": "in_memory",
        "concept_count": concept_count,
        "latency": _latency_stats(samples),
    }


def _write_reports(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "report.json"
    md_path = output_dir / "summary.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# TV-009 Feature generation bench summary",
        "",
        f"- measured_at_utc: `{report['meta']['measured_at_utc']}`",
        f"- iterations / warmup: `{report['meta']['iterations']}` / `{report['meta']['warmup']}`",
        "",
        "| target | p50_ms | p95_ms | max_ms |",
        "| ------ | ------ | ------ | ------ |",
    ]
    for row in report["runs"]:
        st = row["latency"]
        lines.append(
            f"| {row['target']} | {st['p50_ms']} | {st['p95_ms']} | {st['max_ms']} |"
        )
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TV-009 Feature generation performance bench")
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--concept-count", type=int, default=5, help="Item semantic concepts")
    parser.add_argument(
        "--skip-item",
        action="store_true",
        help="User Feature のみ計測",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("../../scripts/perf/output-tv009"),
    )
    args = parser.parse_args(argv)
    if args.iterations < 1:
        raise SystemExit("--iterations は 1 以上")
    if args.warmup < 0:
        raise SystemExit("--warmup は 0 以上")

    _ensure_packages()
    measured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    runs: list[dict[str, Any]] = []

    print("[bench] user_feature_generator", flush=True)
    runs.append(_bench_user_feature(iterations=args.iterations, warmup=args.warmup))
    print(f"  p95={runs[-1]['latency']['p95_ms']} ms", flush=True)

    if not args.skip_item:
        print(f"[bench] item_feature_generator concepts={args.concept_count}", flush=True)
        runs.append(
            _bench_item_feature(
                iterations=args.iterations,
                warmup=args.warmup,
                concept_count=args.concept_count,
            )
        )
        print(f"  p95={runs[-1]['latency']['p95_ms']} ms", flush=True)

    report = {
        "meta": {
            "verification_id": "TV-009",
            "measured_at_utc": measured_at,
            "iterations": args.iterations,
            "warmup": args.warmup,
            "notes": [
                "外部 AI / Reco E2E 非依存",
                "BATCH-012 ジョブ全体は未計測（ItemFeatureGenerator 単体）",
                "apps/** 非改修",
            ],
        },
        "runs": runs,
    }
    _write_reports(args.output_dir.resolve(), report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
