#!/usr/bin/env python3
"""Reco pipeline performance bench harness (Epic #759 / TV-007).

Phase1: ``skeleton`` mode measures Phase4a scaffold pipeline without changing apps/reco.
Phase2: ``live`` mode is reserved for poc-live-verification (Epic #260).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# TV-007 主対象: 入力解析〜 Ranking（Reason は参考計測）
TV007_STEP_PHASES: tuple[str, ...] = (
    "input_parse",
    "user_feature",
    "retrieval",
    "matching",
    "ranking",
)

REFERENCE_STEP_PHASES: tuple[str, ...] = ("reason",)

# 検証計画書 §6 計測ポイント ID へのマッピング（skeleton 近似）
STEP_TO_MEASUREMENT_POINT: dict[str, str] = {
    "input_parse": "input_parse",
    "user_feature": "user_meaning",
    "retrieval": "retrieval",
    "matching": "matching",
    "ranking": "ranking",
    "reason": "reason",
}

PHASE_GROUP_STEPS: dict[str, tuple[str, ...]] = {
    "phase_config": ("input_parse",),
    "phase_user_meaning": ("user_feature",),
    "phase_retrieval": ("retrieval",),
    "phase_matching": ("matching",),
    "phase_ranking": ("ranking",),
    "phase_output": ("reason",),
}

THRESHOLDS_MS: dict[str, float] = {
    "pipeline_total_soft": 2_000.0,
    "pipeline_total_hard": 4_000.0,
    "phase_config": 300.0,
    "phase_user_meaning": 1_000.0,
    "phase_retrieval": 1_000.0,
    "phase_matching": 500.0,
    "phase_ranking": 1_000.0,
    "phase_output": 500.0,
}


@dataclass(frozen=True)
class IterationSample:
    step_timings_ms: dict[str, float]
    pipeline_total_ms: float
    tv007_total_ms: float


def percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * (p / 100.0)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * weight


def summarize_ms(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    return {
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
        "mean_ms": statistics.fmean(ordered),
        "p50_ms": percentile(ordered, 50),
        "p95_ms": percentile(ordered, 95),
    }


def ensure_reco_importable() -> None:
    try:
        import reco  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "reco パッケージを import できません。"
            " apps/reco で `uv sync` 後、`uv run python scripts/perf/reco_pipeline_bench.py` を実行してください。"
            f" detail={exc}"
        ) from exc


def build_initial_context():
    from reco.domain.recommendation.request import RecommendationRequest
    from reco.pipeline.context import PipelineContext

    return PipelineContext(
        recommendation_request_id="bench-request-001",
        recommendation_request=RecommendationRequest(request_id="bench-request-001"),
    )


def run_skeleton_iteration() -> IterationSample:
    from reco.pipeline.runner import PipelineRunner
    from reco.pipeline.stages import DEFAULT_PIPELINE_STEPS

    runner = PipelineRunner(steps=DEFAULT_PIPELINE_STEPS)
    step_timings_ms: dict[str, float] = {}

    pipeline_start = time.perf_counter()
    context = build_initial_context()

    for step in runner.steps:
        phase = getattr(step, "phase", step.__class__.__name__)
        step_start = time.perf_counter()
        context = step.execute(context)
        step_timings_ms[phase] = (time.perf_counter() - step_start) * 1_000.0

    pipeline_total_ms = (time.perf_counter() - pipeline_start) * 1_000.0
    tv007_total_ms = sum(step_timings_ms.get(phase, 0.0) for phase in TV007_STEP_PHASES)

    return IterationSample(
        step_timings_ms=step_timings_ms,
        pipeline_total_ms=pipeline_total_ms,
        tv007_total_ms=tv007_total_ms,
    )


def aggregate_phase_groups(step_stats: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    grouped: dict[str, dict[str, float]] = {}
    for group_id, phases in PHASE_GROUP_STEPS.items():
        p95_values = [
            step_stats[phase]["p95_ms"]
            for phase in phases
            if phase in step_stats
        ]
        if not p95_values:
            continue
        grouped[group_id] = {
            "p95_ms": max(p95_values),
            "hard_limit_ms": THRESHOLDS_MS.get(group_id, 0.0),
        }
    return grouped


def build_report(
    *,
    mode: str,
    iterations: int,
    samples: list[IterationSample],
) -> dict[str, Any]:
    step_series: dict[str, list[float]] = {}
    pipeline_totals: list[float] = []
    tv007_totals: list[float] = []

    for sample in samples:
        pipeline_totals.append(sample.pipeline_total_ms)
        tv007_totals.append(sample.tv007_total_ms)
        for phase, elapsed in sample.step_timings_ms.items():
            step_series.setdefault(phase, []).append(elapsed)

    step_stats = {phase: summarize_ms(values) for phase, values in step_series.items()}
    measurement_points = {
        STEP_TO_MEASUREMENT_POINT[phase]: stats
        for phase, stats in step_stats.items()
        if phase in STEP_TO_MEASUREMENT_POINT
    }

    tv007_summary = summarize_ms(tv007_totals)
    pipeline_summary = summarize_ms(pipeline_totals)

    return {
        "meta": {
            "generated_at": datetime.now(UTC).isoformat(),
            "mode": mode,
            "iterations": iterations,
            "tv007_scope": list(TV007_STEP_PHASES),
            "reference_steps": list(REFERENCE_STEP_PHASES),
        },
        "steps": step_stats,
        "measurement_points": measurement_points,
        "phase_groups": aggregate_phase_groups(step_stats),
        "pipeline_total": {
            **pipeline_summary,
            "tv007_wall_clock": tv007_summary,
            "soft_limit_ms": THRESHOLDS_MS["pipeline_total_soft"],
            "hard_limit_ms": THRESHOLDS_MS["pipeline_total_hard"],
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    meta = report["meta"]
    lines = [
        "# Reco Pipeline Bench Summary",
        "",
        f"- mode: `{meta['mode']}`",
        f"- iterations: {meta['iterations']}",
        f"- generated_at: {meta['generated_at']}",
        "",
        "## TV-007 pipeline total (input_parse → ranking)",
        "",
        "| metric | ms |",
        "| ------ | --: |",
    ]

    total = report["pipeline_total"]["tv007_wall_clock"]
    for key in ("p50_ms", "p95_ms", "mean_ms", "max_ms"):
        lines.append(f"| {key} | {total[key]:.3f} |")

    lines.extend(
        [
            "",
            f"- soft limit: {report['pipeline_total']['soft_limit_ms']:.0f} ms",
            f"- hard limit: {report['pipeline_total']['hard_limit_ms']:.0f} ms",
            "",
            "## Step timings (p50 / p95 ms)",
            "",
            "| step | measurement_point | p50 | p95 |",
            "| ---- | ----------------- | --: | --: |",
        ]
    )

    for phase, stats in report["steps"].items():
        point = STEP_TO_MEASUREMENT_POINT.get(phase, phase)
        lines.append(
            f"| `{phase}` | `{point}` | {stats['p50_ms']:.3f} | {stats['p95_ms']:.3f} |"
        )

    lines.extend(["", "## Phase groups (p95 vs hard limit)", "", "| group | p95 ms | hard ms |", "| ----- | -----: | ------: |"])
    for group_id, stats in report["phase_groups"].items():
        lines.append(
            f"| `{group_id}` | {stats['p95_ms']:.3f} | {stats['hard_limit_ms']:.0f} |"
        )

    if meta["mode"] == "live":
        lines.append("")
        lines.append("> live mode: Phase2 実装（Epic #260）で計測。")
    else:
        lines.append("")
        lines.append(
            "> skeleton mode: scaffold 実測。絶対値は Phase1 下限参考。最終判定は Phase2 live 実測後。"
        )

    return "\n".join(lines) + "\n"


def run_live_mode() -> None:
    raise SystemExit(
        "live mode は Phase2（Epic #260 / poc-live-verification）で有効化予定です。"
        " 現時点では --mode skeleton を使用してください。"
        " 詳細: scripts/perf/README.md"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reco pipeline performance bench (TV-007)")
    parser.add_argument(
        "--mode",
        choices=("skeleton", "live"),
        default="skeleton",
        help="skeleton: Phase4a scaffold 実測 / live: Phase2 予約",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=50,
        help="計測繰り返し回数（p50/p95 算出用）",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("scripts/perf/output"),
        help="JSON / Markdown 出力ディレクトリ",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=3,
        help="計測前ウォームアップ回数（集計対象外）",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.iterations < 1:
        raise SystemExit("--iterations は 1 以上を指定してください")
    if args.warmup < 0:
        raise SystemExit("--warmup は 0 以上を指定してください")

    if args.mode == "live":
        run_live_mode()

    ensure_reco_importable()

    for _ in range(args.warmup):
        run_skeleton_iteration()

    samples = [run_skeleton_iteration() for _ in range(args.iterations)]
    report = build_report(mode=args.mode, iterations=args.iterations, samples=samples)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "report.json"
    md_path = args.output_dir / "summary.md"

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print(
        f"tv007_total p95={report['pipeline_total']['tv007_wall_clock']['p95_ms']:.3f}ms "
        f"(iterations={args.iterations}, mode={args.mode})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
