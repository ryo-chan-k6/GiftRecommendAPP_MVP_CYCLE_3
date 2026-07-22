#!/usr/bin/env python3
"""TV-006: pgvector 類似検索の件数別・HNSW index 効果計測。

本番 `item_embedding.embedding_vector`（vector(1536) + HNSW cosine）と同型の
一時 UNLOGGED テーブルで計測する。item / FK を汚さず件数スケールを再現する。

production DB 禁止。DATABASE_URL は local / ephemeral のみ。
secret 実値はログ・成果物へ出さない。

実行例（apps/reco の uv 環境）:

  set -a && source ../../.env && set +a   # DATABASE_URL のみ。echo しない
  cd apps/reco
  uv run python ../../scripts/perf/pgvector_search_bench.py \\
    --scales 100,500,1000 --top-k 5,20 --iterations 30 --warmup 3 \\
    --output-dir ../../scripts/perf/output-tv006
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_DIMS = 1536
_TABLE = "tv006_pgvector_bench"
_INDEX = "idx_tv006_pgvector_bench_hnsw"
_HNSW_WITH = "WITH (m = 16, ef_construction = 64)"


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


def _redact_database_url(url: str) -> str:
    """Host/db only. Never keep userinfo."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "?"
        port = f":{parsed.port}" if parsed.port else ""
        db = (parsed.path or "/").lstrip("/") or "?"
        return f"postgresql://{host}{port}/{db}"
    except Exception:
        return "(unparseable)"


def _require_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise SystemExit(
            "DATABASE_URL が必要です。"
            " local / ephemeral の URL を env から注入し、成果物へ実値を記載しません。"
        )
    # Heuristic: refuse obvious production hosts if marked
    lowered = url.lower()
    if any(token in lowered for token in ("prod", "production", "neon.tech/prod")):
        # soft guard — still allow if Human overrides with --allow-non-local
        pass
    return url


def _assert_localish(url: str, *, allow_non_local: bool) -> None:
    if allow_non_local:
        return
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in {"127.0.0.1", "localhost", "::1"}:
        return
    # Docker / WSL often uses host.docker.internal or container network names
    if host.endswith(".local") or "supabase" in host or host.startswith("172."):
        return
    raise SystemExit(
        f"DATABASE_URL host={host!r} は local 判定外です。"
        " production 禁止。意図的な場合のみ --allow-non-local を付けてください。"
    )


def _unit_vector(rng: random.Random, dims: int) -> list[float]:
    raw = [rng.gauss(0.0, 1.0) for _ in range(dims)]
    norm = math.sqrt(sum(v * v for v in raw)) or 1.0
    return [v / norm for v in raw]


def _vector_literal(values: list[float]) -> str:
    # pgvector text input: '[v1,v2,...]'
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


def _ensure_extension(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()


def _drop_bench(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {_TABLE}")
    conn.commit()


def _create_bench_table(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            CREATE UNLOGGED TABLE {_TABLE} (
              id bigserial PRIMARY KEY,
              embedding vector({_DIMS}) NOT NULL
            )
            """
        )
    conn.commit()


def _seed_rows(conn: Any, *, count: int, seed: int) -> None:
    batch: list[tuple[str]] = []
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE {_TABLE} RESTART IDENTITY")
        for i in range(count):
            # Slightly vary seed per row for diversity while remaining deterministic
            vec = _unit_vector(random.Random(seed * 1_000_003 + i), _DIMS)
            batch.append((_vector_literal(vec),))
            if len(batch) >= 100:
                cur.executemany(
                    f"INSERT INTO {_TABLE} (embedding) VALUES (%s::vector)",
                    batch,
                )
                batch.clear()
        if batch:
            cur.executemany(
                f"INSERT INTO {_TABLE} (embedding) VALUES (%s::vector)",
                batch,
            )
    conn.commit()


def _drop_hnsw(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute(f"DROP INDEX IF EXISTS {_INDEX}")
    conn.commit()


def _create_hnsw(conn: Any) -> float:
    t0 = time.perf_counter()
    with conn.cursor() as cur:
        cur.execute(
            f"""
            CREATE INDEX {_INDEX}
              ON {_TABLE}
              USING hnsw (embedding vector_cosine_ops)
              {_HNSW_WITH}
            """
        )
    conn.commit()
    return (time.perf_counter() - t0) * 1000.0


def _row_count(conn: Any) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM {_TABLE}")
        row = cur.fetchone()
        return int(row[0])


def _explain_plan(conn: Any, *, query_vec: str, top_k: int) -> str:
    sql = f"""
EXPLAIN (FORMAT TEXT)
SELECT id, (1.0 - (embedding <=> %s::vector))::float8 AS similarity
FROM {_TABLE}
ORDER BY embedding <=> %s::vector
LIMIT %s
"""
    with conn.cursor() as cur:
        cur.execute(sql, (query_vec, query_vec, top_k))
        lines = [r[0] for r in cur.fetchall()]
    return "\n".join(lines)


def _sanitize_explain(plan: str) -> str:
    """EXPLAIN 内の巨大な vector リテラルを短縮する（成果物肥大化防止）。"""
    return re.sub(
        r"'?\[[-0-9eE.,\s]+\]'::vector",
        "'[query_vector_redacted]'::vector",
        plan,
    )


def _detect_scan_kind(plan: str) -> str:
    lowered = plan.lower()
    if "index" in lowered and "scan" in lowered:
        return "index_scan"
    if "seq scan" in lowered:
        return "seq_scan"
    return "unknown"


def _run_queries(
    conn: Any,
    *,
    query_vec: str,
    top_k: int,
    iterations: int,
    warmup: int,
) -> list[float]:
    sql = f"""
SELECT id, (1.0 - (embedding <=> %s::vector))::float8 AS similarity
FROM {_TABLE}
ORDER BY embedding <=> %s::vector
LIMIT %s
"""
    samples: list[float] = []
    with conn.cursor() as cur:
        for i in range(warmup + iterations):
            t0 = time.perf_counter()
            cur.execute(sql, (query_vec, query_vec, top_k))
            _ = cur.fetchall()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            if i >= warmup:
                samples.append(elapsed_ms)
    return samples


def _parse_int_list(raw: str) -> list[int]:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise SystemExit(f"空の整数リストです: {raw!r}")
    out = [int(p) for p in parts]
    if any(v <= 0 for v in out):
        raise SystemExit(f"正の整数のみ: {raw!r}")
    return out


def _write_reports(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "report.json"
    md_path = output_dir / "summary.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines: list[str] = [
        "# TV-006 pgvector search bench summary",
        "",
        f"- measured_at_utc: `{report['meta']['measured_at_utc']}`",
        f"- database: `{report['meta']['database_redacted']}`",
        f"- dims: `{report['meta']['dims']}`",
        f"- iterations / warmup: `{report['meta']['iterations']}` / `{report['meta']['warmup']}`",
        "",
        "| scale | index | top_k | p50_ms | p95_ms | max_ms | plan |",
        "| ----- | ----- | ----- | ------ | ------ | ------ | ---- |",
    ]
    for row in report["runs"]:
        st = row["latency"]
        lines.append(
            "| {scale} | {index_mode} | {top_k} | {p50} | {p95} | {mx} | {plan} |".format(
                scale=row["scale"],
                index_mode=row["index_mode"],
                top_k=row["top_k"],
                p50=st["p50_ms"],
                p95=st["p95_ms"],
                mx=st["max_ms"],
                plan=row["scan_kind"],
            )
        )
    lines.extend(["", "## index build", ""])
    for scale, ms in report.get("index_build_ms_by_scale", {}).items():
        lines.append(f"- scale={scale}: build_ms={ms}")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TV-006 pgvector search performance bench")
    parser.add_argument("--scales", default="100,500,1000", help="comma-separated row counts")
    parser.add_argument("--top-k", default="5,20", dest="top_k", help="comma-separated LIMIT values")
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("../../scripts/perf/output-tv006"),
    )
    parser.add_argument(
        "--allow-non-local",
        action="store_true",
        help="local 以外の DATABASE_URL を許可（通常は使わない）",
    )
    parser.add_argument(
        "--keep-table",
        action="store_true",
        help="計測後に UNLOGGED テーブルを残す（既定は DROP）",
    )
    args = parser.parse_args(argv)

    if args.iterations < 1:
        raise SystemExit("--iterations は 1 以上")
    if args.warmup < 0:
        raise SystemExit("--warmup は 0 以上")

    scales = _parse_int_list(args.scales)
    top_ks = _parse_int_list(args.top_k)

    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit(
            "psycopg が必要です。apps/reco で `uv sync` 後に "
            "`uv run python ../../scripts/perf/pgvector_search_bench.py` を実行してください。"
        ) from exc

    db_url = _require_database_url()
    _assert_localish(db_url, allow_non_local=args.allow_non_local)

    measured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    query_rng = random.Random(args.seed ^ 0xA5A5)
    query_vec = _vector_literal(_unit_vector(query_rng, _DIMS))

    runs: list[dict[str, Any]] = []
    index_build_ms_by_scale: dict[str, float] = {}

    with psycopg.connect(db_url) as conn:
        _ensure_extension(conn)
        _drop_bench(conn)
        _create_bench_table(conn)

        for scale in scales:
            print(f"[seed] scale={scale}", flush=True)
            _drop_hnsw(conn)
            _seed_rows(conn, count=scale, seed=args.seed)
            actual = _row_count(conn)
            if actual != scale:
                raise SystemExit(f"seed 件数不一致: expected={scale} actual={actual}")

            # --- HNSW（小件数では planner が Seq Scan を選びやすいため、
            # index 経路を強制して「index ありの実効」を測る）---
            print(f"[index] create HNSW scale={scale}", flush=True)
            build_ms = _create_hnsw(conn)
            index_build_ms_by_scale[str(scale)] = round(build_ms, 3)
            with conn.cursor() as cur:
                cur.execute("SET enable_seqscan = off")
                cur.execute("RESET enable_indexscan")
                cur.execute("RESET enable_bitmapscan")

            for top_k in top_ks:
                plan = _explain_plan(conn, query_vec=query_vec, top_k=top_k)
                scan_kind = _detect_scan_kind(plan)
                samples = _run_queries(
                    conn,
                    query_vec=query_vec,
                    top_k=top_k,
                    iterations=args.iterations,
                    warmup=args.warmup,
                )
                runs.append(
                    {
                        "scale": scale,
                        "index_mode": "hnsw",
                        "top_k": top_k,
                        "row_count": actual,
                        "scan_kind": scan_kind,
                        "explain_plan": _sanitize_explain(plan),
                        "planner_note": "enable_seqscan=off（HNSW 経路強制）",
                        "latency": _latency_stats(samples),
                        "index_build_ms": round(build_ms, 3),
                    }
                )
                print(
                    f"  hnsw scale={scale} top_k={top_k} "
                    f"p95={runs[-1]['latency']['p95_ms']} plan={scan_kind}",
                    flush=True,
                )

            # --- seqscan（index なし）---
            print(f"[index] drop HNSW scale={scale}", flush=True)
            _drop_hnsw(conn)
            with conn.cursor() as cur:
                cur.execute("RESET enable_seqscan")
                cur.execute("SET enable_indexscan = off")
                cur.execute("SET enable_bitmapscan = off")

            for top_k in top_ks:
                plan = _explain_plan(conn, query_vec=query_vec, top_k=top_k)
                scan_kind = _detect_scan_kind(plan)
                samples = _run_queries(
                    conn,
                    query_vec=query_vec,
                    top_k=top_k,
                    iterations=args.iterations,
                    warmup=args.warmup,
                )
                runs.append(
                    {
                        "scale": scale,
                        "index_mode": "seqscan",
                        "top_k": top_k,
                        "row_count": actual,
                        "scan_kind": scan_kind,
                        "explain_plan": _sanitize_explain(plan),
                        "planner_note": "HNSW DROP + enable_indexscan=off",
                        "latency": _latency_stats(samples),
                        "index_build_ms": None,
                    }
                )
                print(
                    f"  seqscan scale={scale} top_k={top_k} "
                    f"p95={runs[-1]['latency']['p95_ms']} plan={scan_kind}",
                    flush=True,
                )

            with conn.cursor() as cur:
                cur.execute("RESET enable_seqscan")
                cur.execute("RESET enable_indexscan")
                cur.execute("RESET enable_bitmapscan")

        if not args.keep_table:
            _drop_bench(conn)
            print("[cleanup] dropped bench table", flush=True)

    report = {
        "meta": {
            "verification_id": "TV-006",
            "measured_at_utc": measured_at,
            "database_redacted": _redact_database_url(db_url),
            "dims": _DIMS,
            "table": _TABLE,
            "hnsw_ops": "vector_cosine_ops",
            "hnsw_with": _HNSW_WITH,
            "scales": scales,
            "top_k": top_ks,
            "iterations": args.iterations,
            "warmup": args.warmup,
            "seed": args.seed,
            "query_shape": (
                "ORDER BY embedding <=> $query::vector LIMIT $top_k "
                "(本番 Retrieval と同型の距離演算。JOIN/item filter は対象外)"
            ),
        },
        "index_build_ms_by_scale": index_build_ms_by_scale,
        "runs": runs,
    }
    _write_reports(args.output_dir.resolve(), report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
