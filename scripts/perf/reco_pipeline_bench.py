#!/usr/bin/env python3
"""Reco pipeline performance bench harness (TV-007 / Phase1–3).

Phase1: ``skeleton`` mode measures Phase4a scaffold pipeline without changing apps/reco.
Phase2: ``live`` mode runs RecommendationOrchestrator (PRODUCTION) with ephemeral DB
        and optional OpenAI secrets clients injected from scripts/perf (apps/reco 非改修).
Phase3: Reason（phase_output）込み E2E を正式主対象。Ranking までと Reason 込みを分離判定。
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

# Phase2 / 比較用: 入力解析〜 Ranking
RANKING_SCOPE_PHASES: tuple[str, ...] = (
    "input_parse",
    "user_feature",
    "retrieval",
    "matching",
    "ranking",
)

# Phase3 主対象: 入力解析〜 Reason（最終レスポンス）
REASON_E2E_PHASES: tuple[str, ...] = (
    *RANKING_SCOPE_PHASES,
    "reason",
)

# 後方互換エイリアス（Phase2 スクリプト・docs 参照）
TV007_STEP_PHASES: tuple[str, ...] = RANKING_SCOPE_PHASES
REFERENCE_STEP_PHASES: tuple[str, ...] = ("reason",)

# 検証計画書 §6 計測ポイント ID へのマッピング
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

# Orchestrator 集約 phase_name → TV-007 step（duration 合算）
# #1545: response_built は累積壁時計のため reason / phase_output 合算から除外し、
# 診断用メトリクス `response_built` として別集計する。
LIVE_PHASE_TO_STEP: dict[str, str] = {
    "request_received": "input_parse",
    "config_resolved": "input_parse",
    "semantic_extracted": "user_feature",
    "user_feature_generated": "user_feature",
    "user_meaning_projected": "user_feature",
    "query_embedding_generated": "user_feature",
    "pre_hard_filter_completed": "retrieval",
    "retrieval_completed": "retrieval",
    "post_hard_filter_completed": "retrieval",
    "matching_completed": "matching",
    "ranking_completed": "ranking",
    "result_generated": "reason",
    "reason_generated": "reason",
    "response_built": "response_built",
}

# phase_output（reason step）に含める Orchestrator phase（response_built 除外後）
PHASE_OUTPUT_LIVE_PHASES: tuple[str, ...] = ("result_generated", "reason_generated")

# #1533 Human 確定: Reco 内部 / 同期外部 AI 込み。phase_output は Phase3 で案出し（暫定 500 を参考維持）
THRESHOLDS_MS: dict[str, float] = {
    "internal_soft": 1_500.0,
    "internal_hard": 2_000.0,
    "sync_external_ai_soft": 6_000.0,
    "sync_external_ai_hard": 8_000.0,
    # 後方互換（Phase2 旧 soft/hard。report では internal / sync_external_ai を優先）
    "pipeline_total_soft": 1_500.0,
    "pipeline_total_hard": 2_000.0,
    "phase_config": 300.0,
    "phase_user_meaning": 5_000.0,
    "phase_retrieval": 1_000.0,
    "phase_matching": 500.0,
    "phase_ranking": 1_000.0,
    "phase_output": 500.0,
}

DEFAULT_RELATIONSHIP_CODE = "friend_casual"
DEFAULT_OCCASION_CODE = "birthday"


@dataclass(frozen=True)
class IterationSample:
    step_timings_ms: dict[str, float]
    pipeline_total_ms: float
    ranking_until_ms: float
    reason_e2e_ms: float
    success: bool = True
    error_code: str | None = None

    @property
    def tv007_total_ms(self) -> float:
        """後方互換: Phase2 相当（Ranking まで）。"""
        return self.ranking_until_ms


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
    if not values:
        return {
            "min_ms": 0.0,
            "max_ms": 0.0,
            "mean_ms": 0.0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
        }
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
    ranking_until_ms = sum(step_timings_ms.get(phase, 0.0) for phase in RANKING_SCOPE_PHASES)
    reason_e2e_ms = sum(step_timings_ms.get(phase, 0.0) for phase in REASON_E2E_PHASES)
    if reason_e2e_ms <= 0:
        reason_e2e_ms = pipeline_total_ms

    return IterationSample(
        step_timings_ms=step_timings_ms,
        pipeline_total_ms=pipeline_total_ms,
        ranking_until_ms=ranking_until_ms,
        reason_e2e_ms=reason_e2e_ms,
    )


def _scripts_perf_dir() -> Path:
    return Path(__file__).resolve().parent


def _ensure_openai_clients_importable() -> None:
    """Allow `import openai_bench_clients` when running from apps/reco cwd."""
    perf_dir = str(_scripts_perf_dir())
    if perf_dir not in sys.path:
        sys.path.insert(0, perf_dir)


def _phase_events_to_step_timings(phase_log_events: list[dict[str, object]]) -> dict[str, float]:
    """Sum SUCCEEDED duration_ms per TV-007 step from Orchestrator phase_log_events.

    ``response_built`` is tracked as its own key and is **not** folded into ``reason`` /
    ``phase_output`` (Issue #1545). Reason E2E wall-clock remains ``pipeline_total_ms``.
    """
    step_timings: dict[str, float] = {
        phase: 0.0 for phase in (*TV007_STEP_PHASES, *REFERENCE_STEP_PHASES, "response_built")
    }
    for event in phase_log_events:
        status = str(event.get("phase_status", ""))
        if status not in {"succeeded", "PhaseStatus.SUCCEEDED", "SUCCEEDED"}:
            # PhaseStatus enum may serialize as "succeeded"
            status_norm = status.lower().replace("phasestatus.", "")
            if status_norm != "succeeded":
                continue
        phase_name = event.get("phase_name")
        duration = event.get("duration_ms")
        if not isinstance(phase_name, str) or duration is None:
            continue
        try:
            duration_f = float(duration)
        except (TypeError, ValueError):
            continue
        step = LIVE_PHASE_TO_STEP.get(phase_name)
        if step is None:
            continue
        step_timings[step] = step_timings.get(step, 0.0) + duration_f
    return step_timings


def _insert_recommendation_request(
    session: Any,
    *,
    request_id: str,
    trace_id: str,
    relationship_code: str,
    occasion_code: str,
    top_k: int,
) -> None:
    payload = {
        "request_id": request_id,
        "relationship_code": relationship_code,
        "occasion_code": occasion_code,
    }
    session.execute(
        """
        INSERT INTO recommendation_request (
          recommendation_request_id,
          request_mode,
          relationship_code,
          occasion_code,
          currency,
          top_k,
          request_payload,
          validated_payload,
          trace_id,
          validated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
        ON CONFLICT (recommendation_request_id) DO NOTHING
        """,
        (
            request_id,
            "ui",
            relationship_code,
            occasion_code,
            "JPY",
            top_k,
            json.dumps(payload, ensure_ascii=False),
            json.dumps(payload, ensure_ascii=False),
            trace_id,
            datetime.now(UTC),
        ),
    )


def _inject_openai_clients(ports: Any, *, openai_mode: str) -> tuple[Any, dict[str, Any]]:
    """Replace scaffold Embedding/LLM clients when openai_mode=secrets (apps/reco 非改修)."""
    meta: dict[str, Any] = {
        "openai_mode": openai_mode,
        "embedding_client": "scaffold_or_in_memory",
        "llm_client": "scaffold",
        "embedding_calls": 0,
        "llm_calls": 0,
    }
    if openai_mode != "secrets":
        return ports, meta

    _ensure_openai_clients_importable()
    from openai_bench_clients import HttpOpenAiEmbeddingClient, HttpOpenAiLlmClient

    embedding_client = HttpOpenAiEmbeddingClient()
    llm_client = HttpOpenAiLlmClient()
    ports = replace(
        ports,
        query_embedding_generator=replace(
            ports.query_embedding_generator,
            embedding_client=embedding_client,
        ),
        user_semantic_extractor=replace(
            ports.user_semantic_extractor,
            llm_client=llm_client,
        ),
        reason_generator=replace(
            ports.reason_generator,
            llm_client=llm_client,
        ),
    )
    meta["embedding_client"] = "http_openai"
    meta["llm_client"] = "http_openai"
    meta["_embedding_client_ref"] = embedding_client
    meta["_llm_client_ref"] = llm_client
    return ports, meta


def _build_live_orchestrator(
    *,
    openai_mode: str,
    database_url: str | None,
    bypass_hard_timeout: bool,
) -> tuple[Any, Any, dict[str, Any]]:
    # hyphenated application packages を先に登録してから Orchestrator を import する
    from reco.composition.bootstrap import ensure_composition_application_packages

    ensure_composition_application_packages()

    from reco.application.recommendation_orchestrator import RecommendationOrchestrator
    from reco.composition import CompositionMode, build_composition_ports
    from reco.composition.config import resolve_database_url
    from reco.infrastructure.db.session import create_database_session

    resolved_url = resolve_database_url(database_url)
    session = create_database_session(resolved_url)
    ports, helpers = build_composition_ports(
        CompositionMode.PRODUCTION,
        database_session=session,
    )
    ports, openai_meta = _inject_openai_clients(ports, openai_mode=openai_mode)

    elapsed_provider = (lambda: 0) if bypass_hard_timeout else None
    orchestrator = RecommendationOrchestrator(
        ports=ports,
        elapsed_ms_provider=elapsed_provider,
    )
    meta = {
        **openai_meta,
        "database_url_configured": True,
        "bypass_hard_timeout": bypass_hard_timeout,
        "composition_mode": "PRODUCTION",
    }
    return orchestrator, session, meta


def run_live_iteration(
    orchestrator: Any,
    session: Any,
    *,
    relationship_code: str,
    occasion_code: str,
    top_k: int,
    candidate_limit: int,
    free_text: str | None,
) -> IterationSample:
    from reco.domain import (
        ExecutionCondition,
        ExecutionMode,
        OccasionCondition,
        PreferredCondition,
        RecommendationRequest,
        RelationshipCondition,
    )

    request_id = str(uuid4())
    trace_id = f"bench-live-{request_id[:8]}"
    _insert_recommendation_request(
        session,
        request_id=request_id,
        trace_id=trace_id,
        relationship_code=relationship_code,
        occasion_code=occasion_code,
        top_k=top_k,
    )

    preferred = None
    if free_text:
        preferred = PreferredCondition(preferred_text=free_text)

    domain_request = RecommendationRequest(
        request_id=request_id,
        relationship=RelationshipCondition(relationship_code=relationship_code),
        occasion=OccasionCondition(occasion_code=occasion_code),
        preferred_condition=preferred,
        free_text=free_text,
        execution=ExecutionCondition(
            mode=ExecutionMode.UI,
            top_k=top_k,
            candidate_limit=candidate_limit,
            include_reason=True,
        ),
    )

    pipeline_start = time.perf_counter()
    outcome = orchestrator.run(domain_request, trace_id=trace_id)
    pipeline_total_ms = (time.perf_counter() - pipeline_start) * 1_000.0

    context = outcome.execution_context
    phase_events: list[dict[str, object]] = []
    if context is not None:
        phase_events = list(context.phase_log_events)

    step_timings_ms = _phase_events_to_step_timings(phase_events)
    ranking_until_ms = sum(step_timings_ms.get(phase, 0.0) for phase in RANKING_SCOPE_PHASES)
    reason_phase_sum_ms = sum(step_timings_ms.get(phase, 0.0) for phase in REASON_E2E_PHASES)

    error_code = None
    if outcome.reco_error is not None:
        error_code = getattr(outcome.reco_error, "error_code", None) or str(outcome.reco_error)

    # Ranking まで: phase 合算。失敗時は wall-clock を下限として採用。
    if not outcome.success and pipeline_total_ms > ranking_until_ms:
        ranking_wall = pipeline_total_ms
    else:
        ranking_wall = ranking_until_ms if ranking_until_ms > 0 else pipeline_total_ms

    # Reason 込み E2E: 最終レスポンス相当は外側 wall-clock を主、phase 合算は補助。
    if reason_phase_sum_ms > 0 and outcome.success:
        reason_e2e_ms = max(pipeline_total_ms, reason_phase_sum_ms)
    else:
        reason_e2e_ms = pipeline_total_ms

    return IterationSample(
        step_timings_ms=step_timings_ms,
        pipeline_total_ms=pipeline_total_ms,
        ranking_until_ms=ranking_wall,
        reason_e2e_ms=reason_e2e_ms,
        success=bool(outcome.success),
        error_code=error_code,
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


def _verdict_label(
    *,
    p95_ms: float,
    soft_ms: float,
    hard_ms: float,
    success_count: int,
) -> dict[str, Any]:
    if success_count == 0:
        return {
            "label": "Block",
            "p95_ms": p95_ms,
            "soft_limit_ms": soft_ms,
            "hard_limit_ms": hard_ms,
            "rule": "p95<=soft→Go; soft<p95<=hard→Adjust; p95>hard→Block; all-fail→Block",
            "note": "all iterations failed; treat as Block regardless of wall-clock",
        }
    if p95_ms <= soft_ms:
        label = "Go"
    elif p95_ms <= hard_ms:
        label = "Adjust"
    else:
        label = "Block"
    return {
        "label": label,
        "p95_ms": p95_ms,
        "soft_limit_ms": soft_ms,
        "hard_limit_ms": hard_ms,
        "rule": "p95<=soft→Go; soft<p95<=hard→Adjust; p95>hard→Block; all-fail→Block",
        "note": None,
    }


def build_report(
    *,
    mode: str,
    iterations: int,
    samples: list[IterationSample],
    extra_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    step_series: dict[str, list[float]] = {}
    pipeline_totals: list[float] = []
    ranking_totals: list[float] = []
    reason_e2e_totals: list[float] = []
    success_count = 0
    error_codes: dict[str, int] = {}

    for sample in samples:
        pipeline_totals.append(sample.pipeline_total_ms)
        ranking_totals.append(sample.ranking_until_ms)
        reason_e2e_totals.append(sample.reason_e2e_ms)
        if sample.success:
            success_count += 1
        if sample.error_code:
            error_codes[sample.error_code] = error_codes.get(sample.error_code, 0) + 1
        for phase, elapsed in sample.step_timings_ms.items():
            step_series.setdefault(phase, []).append(elapsed)

    step_stats = {phase: summarize_ms(values) for phase, values in step_series.items()}
    measurement_points = {
        STEP_TO_MEASUREMENT_POINT[phase]: stats
        for phase, stats in step_stats.items()
        if phase in STEP_TO_MEASUREMENT_POINT
    }

    ranking_summary = summarize_ms(ranking_totals)
    reason_e2e_summary = summarize_ms(reason_e2e_totals)
    pipeline_summary = summarize_ms(pipeline_totals)
    phase_output_stats = step_stats.get("reason", summarize_ms([]))
    response_built_stats = step_stats.get("response_built", summarize_ms([]))

    internal_soft = THRESHOLDS_MS["internal_soft"]
    internal_hard = THRESHOLDS_MS["internal_hard"]
    sync_soft = THRESHOLDS_MS["sync_external_ai_soft"]
    sync_hard = THRESHOLDS_MS["sync_external_ai_hard"]

    ranking_verdict = _verdict_label(
        p95_ms=ranking_summary["p95_ms"],
        soft_ms=internal_soft,
        hard_ms=internal_hard,
        success_count=success_count,
    )
    reason_verdict = _verdict_label(
        p95_ms=reason_e2e_summary["p95_ms"],
        soft_ms=sync_soft,
        hard_ms=sync_hard,
        success_count=success_count,
    )

    meta: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": mode,
        "iterations": iterations,
        "primary_scope": "reason_e2e",
        "ranking_scope": list(RANKING_SCOPE_PHASES),
        "reason_e2e_scope": list(REASON_E2E_PHASES),
        "tv007_scope": list(RANKING_SCOPE_PHASES),
        "reference_steps": list(REFERENCE_STEP_PHASES),
        "phase_output_live_phases": list(PHASE_OUTPUT_LIVE_PHASES),
        "phase_output_excludes": ["response_built"],
        "success_count": success_count,
        "failure_count": iterations - success_count,
        "error_codes": error_codes,
        "verdict_ranking_until_vs_internal": ranking_verdict,
        "verdict_reason_e2e_vs_sync_external_ai": reason_verdict,
        # Phase2 互換: Ranking まで vs Reco 内部 soft/hard
        "verdict_vs_soft_hard": {
            **ranking_verdict,
            "tv007_p95_ms": ranking_verdict["p95_ms"],
            "scope": "ranking_until_vs_internal",
        },
        "thresholds_ms": {
            "internal_soft": internal_soft,
            "internal_hard": internal_hard,
            "sync_external_ai_soft": sync_soft,
            "sync_external_ai_hard": sync_hard,
            "phase_output_provisional": THRESHOLDS_MS["phase_output"],
        },
    }
    if extra_meta:
        safe_meta = {
            key: value
            for key, value in extra_meta.items()
            if not key.startswith("_")
        }
        meta.update(safe_meta)

    return {
        "meta": meta,
        "steps": step_stats,
        "measurement_points": measurement_points,
        "phase_groups": aggregate_phase_groups(step_stats),
        "scopes": {
            "ranking_until": {
                **ranking_summary,
                "soft_limit_ms": internal_soft,
                "hard_limit_ms": internal_hard,
                "verdict": ranking_verdict,
            },
            "reason_e2e": {
                **reason_e2e_summary,
                "soft_limit_ms": sync_soft,
                "hard_limit_ms": sync_hard,
                "verdict": reason_verdict,
            },
            "phase_output": {
                **phase_output_stats,
                "provisional_hard_limit_ms": THRESHOLDS_MS["phase_output"],
                "includes_phases": list(PHASE_OUTPUT_LIVE_PHASES),
                "excludes_phases": ["response_built"],
            },
            "response_built": {
                **response_built_stats,
                "note": "diagnostic_only; cumulative wall-clock; excluded from phase_output",
            },
        },
        "pipeline_total": {
            **pipeline_summary,
            "tv007_wall_clock": ranking_summary,
            "reason_e2e_wall_clock": reason_e2e_summary,
            "soft_limit_ms": internal_soft,
            "hard_limit_ms": internal_hard,
            "sync_external_ai_soft_ms": sync_soft,
            "sync_external_ai_hard_ms": sync_hard,
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
        f"- primary_scope: `{meta.get('primary_scope', 'reason_e2e')}`",
    ]
    if "openai_mode" in meta:
        lines.append(f"- openai_mode: `{meta['openai_mode']}`")

    ranking_v = meta.get("verdict_ranking_until_vs_internal") or meta.get("verdict_vs_soft_hard", {})
    reason_v = meta.get("verdict_reason_e2e_vs_sync_external_ai", {})
    if ranking_v:
        lines.append(
            f"- Ranking まで vs Reco内部: **{ranking_v.get('label', 'n/a')}** "
            f"(p95={ranking_v.get('p95_ms', ranking_v.get('tv007_p95_ms', 0)):.3f}ms / "
            f"soft={ranking_v.get('soft_limit_ms', 0):.0f} / hard={ranking_v.get('hard_limit_ms', 0):.0f})"
        )
    if reason_v:
        lines.append(
            f"- Reason込み vs 同期外部AI込み: **{reason_v.get('label', 'n/a')}** "
            f"(p95={reason_v.get('p95_ms', 0):.3f}ms / "
            f"soft={reason_v.get('soft_limit_ms', 0):.0f} / hard={reason_v.get('hard_limit_ms', 0):.0f})"
        )

    scopes = report.get("scopes", {})
    reason_scope = scopes.get("reason_e2e") or report["pipeline_total"].get("reason_e2e_wall_clock")
    ranking_scope = scopes.get("ranking_until") or report["pipeline_total"].get("tv007_wall_clock")
    phase_output = scopes.get("phase_output") or report["steps"].get("reason", {})

    lines.extend(
        [
            "",
            "## Phase3 primary: Reason E2E (input_parse → reason)",
            "",
            "| metric | ms |",
            "| ------ | --: |",
        ]
    )
    if reason_scope:
        for key in ("p50_ms", "p95_ms", "mean_ms", "max_ms"):
            lines.append(f"| {key} | {reason_scope[key]:.3f} |")
        lines.append(
            f"| soft (sync external AI) | {report['pipeline_total'].get('sync_external_ai_soft_ms', 6000):.0f} |"
        )
        lines.append(
            f"| hard (sync external AI) | {report['pipeline_total'].get('sync_external_ai_hard_ms', 8000):.0f} |"
        )

    lines.extend(
        [
            "",
            "## Comparison: Ranking until (input_parse → ranking)",
            "",
            "| metric | ms |",
            "| ------ | --: |",
        ]
    )
    if ranking_scope:
        for key in ("p50_ms", "p95_ms", "mean_ms", "max_ms"):
            lines.append(f"| {key} | {ranking_scope[key]:.3f} |")
        lines.append(f"| soft (Reco internal) | {report['pipeline_total']['soft_limit_ms']:.0f} |")
        lines.append(f"| hard (Reco internal) | {report['pipeline_total']['hard_limit_ms']:.0f} |")

    lines.extend(
        [
            "",
            "## phase_output (reason step; excludes response_built)",
            "",
            "| metric | ms |",
            "| ------ | --: |",
        ]
    )
    for key in ("p50_ms", "p95_ms", "mean_ms", "max_ms"):
        if key in phase_output:
            lines.append(f"| {key} | {phase_output[key]:.3f} |")
    if "provisional_hard_limit_ms" in phase_output:
        lines.append(f"| provisional hard | {phase_output['provisional_hard_limit_ms']:.0f} |")
    includes = phase_output.get("includes_phases") or list(PHASE_OUTPUT_LIVE_PHASES)
    excludes = phase_output.get("excludes_phases") or ["response_built"]
    lines.append(f"| includes | {', '.join(includes)} |")
    lines.append(f"| excludes | {', '.join(excludes)} |")

    response_built = scopes.get("response_built") or report["steps"].get("response_built", {})
    lines.extend(
        [
            "",
            "## response_built (diagnostic; excluded from phase_output)",
            "",
            "| metric | ms |",
            "| ------ | --: |",
        ]
    )
    for key in ("p50_ms", "p95_ms", "mean_ms", "max_ms"):
        if key in response_built:
            lines.append(f"| {key} | {response_built[key]:.3f} |")
    if response_built.get("note"):
        lines.append(f"| note | {response_built['note']} |")

    lines.extend(
        [
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

    lines.extend(
        ["", "## Phase groups (p95 vs hard limit)", "", "| group | p95 ms | hard ms |", "| ----- | -----: | ------: |"]
    )
    for group_id, stats in report["phase_groups"].items():
        lines.append(
            f"| `{group_id}` | {stats['p95_ms']:.3f} | {stats['hard_limit_ms']:.0f} |"
        )

    if meta["mode"] == "live":
        lines.append("")
        lines.append(
            "> live mode: RecommendationOrchestrator (PRODUCTION) + ephemeral DB。"
            " OpenAI secrets は scripts/perf クライアント差込（apps/reco 非改修）。"
            " Phase3 主対象は Reason 込み E2E。判定は Ranking まで（Reco内部）と Reason 込み（同期外部AI込み）を分離。"
        )
    else:
        lines.append("")
        lines.append(
            "> skeleton mode: scaffold 実測。絶対値は Phase1 下限参考。最終判定は live 実測後。"
        )

    return "\n".join(lines) + "\n"


def run_live_mode(args: argparse.Namespace) -> list[IterationSample]:
    if not os.environ.get("DATABASE_URL") and not args.database_url:
        raise SystemExit(
            "live mode には DATABASE_URL（または --database-url）が必要です。"
            " ephemeral DB 手順: scripts/perf/README.md / scripts/db/README.md"
        )

    orchestrator, session, live_meta = _build_live_orchestrator(
        openai_mode=args.openai_mode,
        database_url=args.database_url,
        bypass_hard_timeout=not args.enforce_hard_timeout,
    )
    args._live_meta = live_meta  # noqa: SLF001 - pass meta to main via namespace

    free_text = args.free_text or None
    if args.openai_mode == "secrets" and args.force_llm and not free_text:
        free_text = "温かくて心のこもったギフトを探しています"

    for _ in range(args.warmup):
        run_live_iteration(
            orchestrator,
            session,
            relationship_code=args.relationship_code,
            occasion_code=args.occasion_code,
            top_k=args.top_k,
            candidate_limit=args.candidate_limit,
            free_text=free_text,
        )

    samples = [
        run_live_iteration(
            orchestrator,
            session,
            relationship_code=args.relationship_code,
            occasion_code=args.occasion_code,
            top_k=args.top_k,
            candidate_limit=args.candidate_limit,
            free_text=free_text,
        )
        for _ in range(args.iterations)
    ]

    embedding_ref = live_meta.get("_embedding_client_ref")
    llm_ref = live_meta.get("_llm_client_ref")
    if embedding_ref is not None:
        live_meta["embedding_calls"] = len(getattr(embedding_ref, "generate_calls", []))
    if llm_ref is not None:
        live_meta["llm_calls"] = len(getattr(llm_ref, "generate_calls", []))
    live_meta["relationship_code"] = args.relationship_code
    live_meta["occasion_code"] = args.occasion_code
    live_meta["top_k"] = args.top_k
    live_meta["candidate_limit"] = args.candidate_limit
    live_meta["free_text_used"] = bool(free_text)

    return samples


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reco pipeline performance bench (TV-007)")
    parser.add_argument(
        "--mode",
        choices=("skeleton", "live"),
        default="skeleton",
        help="skeleton: Phase4a scaffold / live: Orchestrator PRODUCTION",
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
    parser.add_argument(
        "--openai-mode",
        choices=("mock", "secrets"),
        default="mock",
        help="live のみ。mock=scaffold Embedding/LLM / secrets=OpenAI HTTP 実疎通",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="live 用 DATABASE_URL 上書き（未指定時は環境変数）",
    )
    parser.add_argument(
        "--relationship-code",
        default=DEFAULT_RELATIONSHIP_CODE,
        help="live 代表入力 relationship_code",
    )
    parser.add_argument(
        "--occasion-code",
        default=DEFAULT_OCCASION_CODE,
        help="live 代表入力 occasion_code",
    )
    parser.add_argument("--top-k", type=int, default=5, help="live Ranking top_k")
    parser.add_argument(
        "--candidate-limit",
        type=int,
        default=100,
        help="live Retrieval candidate_limit",
    )
    parser.add_argument(
        "--free-text",
        default="",
        help="live 自由文（LLM 誘発用。空なら relationship/occasion のみ）",
    )
    parser.add_argument(
        "--force-llm",
        action="store_true",
        help="secrets 時、free_text 未指定なら代表文を付与して LLM 経路を誘発",
    )
    parser.add_argument(
        "--enforce-hard-timeout",
        action="store_true",
        help="live で Orchestrator hard timeout を有効化（既定は計測のため bypass。#1533 本番主経路 hard は 8,000ms）",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.iterations < 1:
        raise SystemExit("--iterations は 1 以上を指定してください")
    if args.warmup < 0:
        raise SystemExit("--warmup は 0 以上を指定してください")

    ensure_reco_importable()
    extra_meta: dict[str, Any] = {}

    if args.mode == "live":
        samples = run_live_mode(args)
        extra_meta = getattr(args, "_live_meta", {}) or {}
    else:
        if args.openai_mode == "secrets":
            print(
                "warning: --openai-mode は live 専用です。skeleton では無視します。",
                file=sys.stderr,
            )
        for _ in range(args.warmup):
            run_skeleton_iteration()
        samples = [run_skeleton_iteration() for _ in range(args.iterations)]

    report = build_report(
        mode=args.mode,
        iterations=args.iterations,
        samples=samples,
        extra_meta=extra_meta,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "report.json"
    md_path = args.output_dir / "summary.md"

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    reason_p95 = report["pipeline_total"]["reason_e2e_wall_clock"]["p95_ms"]
    ranking_p95 = report["pipeline_total"]["tv007_wall_clock"]["p95_ms"]
    reason_label = report["meta"].get("verdict_reason_e2e_vs_sync_external_ai", {}).get("label", "n/a")
    ranking_label = report["meta"].get("verdict_ranking_until_vs_internal", {}).get("label", "n/a")
    print(
        f"reason_e2e p95={reason_p95:.3f}ms ({reason_label}) / "
        f"ranking_until p95={ranking_p95:.3f}ms ({ranking_label}) "
        f"(iterations={args.iterations}, mode={args.mode})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
