#!/usr/bin/env python3
"""TV-005: OpenAI Embedding / LLM 専用疎通計測（Reco E2E 非依存）。

openai_bench_clients.py と同系統の HTTP 呼び出しを、パイプライン外で計測する。
secret 実値は環境変数からのみ読み取り、ログ・成果物へ出さない。

実行例（apps/reco の uv 環境で httpx を利用）:

  set -a && source .env && set +a   # OPENAI_API_KEY のみ。echo しない
  cd apps/reco
  uv run python ../../scripts/perf/openai_connectivity_bench.py \\
    --mode mock --iterations 20 --output-dir ../../scripts/perf/output-tv005-mock

  uv run python ../../scripts/perf/openai_connectivity_bench.py \\
    --mode secrets --iterations 10 --warmup 1 \\
    --output-dir ../../scripts/perf/output-tv005-secrets
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants（公開単価。変更され得るため結果 doc に計測日を残す）
# ---------------------------------------------------------------------------

_OPENAI_BASE_URL = "https://api.openai.com/v1"
_DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
_DEFAULT_CHAT_MODEL = "gpt-4o-mini"
_EMBEDDING_DIMENSIONS = 1536
_TIMEOUT_S = 30.0

# USD per 1M tokens（OpenAI 公開価格帯の目安。2026-07 時点の記録用）
_PRICE_EMBEDDING_PER_1M = 0.02
_PRICE_CHAT_INPUT_PER_1M = 0.15
_PRICE_CHAT_OUTPUT_PER_1M = 0.60

_SAMPLE_EMBED_TEXT = (
    "friend birthday gift recommendation connectivity probe text for TV-005"
)
_SAMPLE_CHAT_PROMPT = (
    "Extract gift semantic concepts as JSON only. "
    'Return {"concepts":[{"concept_code":"warmth","confidence":0.8,'
    '"input_intent":"neutral","evidence_texts":[]}]}'
)


def _redacted_http_error(exc: BaseException) -> str:
    """Avoid echoing response bodies that might contain sensitive upstream data."""
    status = None
    response = getattr(exc, "response", None)
    if response is not None:
        status = getattr(response, "status_code", None)
    if status is not None:
        return f"{type(exc).__name__} status={status} (body redacted for bench safety)"
    return f"{type(exc).__name__} (details redacted for bench safety)"


def _require_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "mode=secrets には OPENAI_API_KEY が必要です。"
            " 実値は env / GitHub Secrets からのみ注入し、成果物へ記載しません。"
        )
    return api_key


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


def _usd_from_tokens(
    *,
    prompt_tokens: int,
    completion_tokens: int,
    embedding_tokens: int,
) -> dict[str, float]:
    embed_usd = embedding_tokens * _PRICE_EMBEDDING_PER_1M / 1_000_000
    chat_usd = (
        prompt_tokens * _PRICE_CHAT_INPUT_PER_1M / 1_000_000
        + completion_tokens * _PRICE_CHAT_OUTPUT_PER_1M / 1_000_000
    )
    return {
        "embedding_usd": round(embed_usd, 8),
        "chat_usd": round(chat_usd, 8),
        "total_usd": round(embed_usd + chat_usd, 8),
    }


@dataclass
class CallRecord:
    api: str
    ok: bool
    latency_ms: float
    error_kind: str | None = None
    error_summary: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    http_status: int | None = None
    response_shape: str | None = None


@dataclass
class BenchResult:
    mode: str
    embedding_model: str
    chat_model: str
    iterations: int
    warmup: int
    measured_at_utc: str
    embedding_latencies_ms: list[float] = field(default_factory=list)
    chat_latencies_ms: list[float] = field(default_factory=list)
    embedding_calls: list[CallRecord] = field(default_factory=list)
    chat_calls: list[CallRecord] = field(default_factory=list)
    failure_probes: list[CallRecord] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_report(self) -> dict[str, Any]:
        embed_ok = [c for c in self.embedding_calls if c.ok]
        chat_ok = [c for c in self.chat_calls if c.ok]
        prompt_tokens = sum(c.prompt_tokens for c in chat_ok)
        completion_tokens = sum(c.completion_tokens for c in chat_ok)
        embedding_tokens = sum(c.total_tokens for c in embed_ok)
        cost = _usd_from_tokens(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            embedding_tokens=embedding_tokens,
        )
        return {
            "tv_id": "TV-005",
            "mode": self.mode,
            "embedding_model": self.embedding_model,
            "chat_model": self.chat_model,
            "iterations": self.iterations,
            "warmup": self.warmup,
            "measured_at_utc": self.measured_at_utc,
            "pricing_note": {
                "unit": "USD per 1M tokens (public list price snapshot for estimate)",
                "embedding_model": self.embedding_model,
                "embedding_per_1m_usd": _PRICE_EMBEDDING_PER_1M,
                "chat_input_per_1m_usd": _PRICE_CHAT_INPUT_PER_1M,
                "chat_output_per_1m_usd": _PRICE_CHAT_OUTPUT_PER_1M,
            },
            "embedding": {
                "success_count": len(embed_ok),
                "failure_count": len(self.embedding_calls) - len(embed_ok),
                "latency": _latency_stats(self.embedding_latencies_ms),
                "token_total": embedding_tokens,
            },
            "chat": {
                "success_count": len(chat_ok),
                "failure_count": len(self.chat_calls) - len(chat_ok),
                "latency": _latency_stats(self.chat_latencies_ms),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "token_total": prompt_tokens + completion_tokens,
            },
            "cost_estimate_usd": cost,
            "failure_probes": [asdict(c) for c in self.failure_probes],
            "notes": self.notes,
            "tv007_boundary": (
                "TV-007 measures OpenAI inside Reco E2E. "
                "TV-005 measures Embedding/LLM connectivity in isolation."
            ),
        }


class MockOpenAiClient:
    """HTTP を撃たず、成功応答と失敗形式を再現する。"""

    def embedding(self, text: str) -> CallRecord:
        started = time.perf_counter()
        time.sleep(0.002)
        latency_ms = (time.perf_counter() - started) * 1000.0
        # おおよそ 1 token ≈ 4 chars の粗い見積
        tokens = max(1, len(text) // 4)
        return CallRecord(
            api="embeddings",
            ok=True,
            latency_ms=latency_ms,
            total_tokens=tokens,
            http_status=200,
            response_shape="data[0].embedding:list[float]",
        )

    def chat(self, prompt: str) -> CallRecord:
        started = time.perf_counter()
        time.sleep(0.005)
        latency_ms = (time.perf_counter() - started) * 1000.0
        prompt_tokens = max(1, len(prompt) // 4)
        completion_tokens = 48
        return CallRecord(
            api="chat.completions",
            ok=True,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            http_status=200,
            response_shape="choices[0].message.content:str(json)",
        )

    def failure_probes(self) -> list[CallRecord]:
        return [
            CallRecord(
                api="embeddings",
                ok=False,
                latency_ms=1.0,
                error_kind="auth",
                error_summary="HTTPStatusError status=401 (body redacted for bench safety)",
                http_status=401,
                response_shape="error.type=invalid_request_error / code=invalid_api_key",
            ),
            CallRecord(
                api="chat.completions",
                ok=False,
                latency_ms=1.0,
                error_kind="rate_limit",
                error_summary="HTTPStatusError status=429 (body redacted for bench safety)",
                http_status=429,
                response_shape="error.type=rate_limit_error / retry-after header may exist",
            ),
            CallRecord(
                api="embeddings",
                ok=False,
                latency_ms=1.0,
                error_kind="timeout",
                error_summary="TimeoutException (details redacted for bench safety)",
                http_status=None,
                response_shape="client timeout before response body",
            ),
        ]


class SecretsOpenAiClient:
    """実 OpenAI HTTP（openai_bench_clients と同系統。apps/reco 非依存）。"""

    def __init__(
        self,
        *,
        embedding_model: str,
        chat_model: str,
        timeout_s: float,
        api_key: str,
    ) -> None:
        import httpx

        self._httpx = httpx
        self.embedding_model = embedding_model
        self.chat_model = chat_model
        self.timeout_s = timeout_s
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def embedding(self, text: str) -> CallRecord:
        payload = {
            "model": self.embedding_model,
            "input": text,
            "dimensions": _EMBEDDING_DIMENSIONS,
        }
        started = time.perf_counter()
        try:
            with self._httpx.Client(timeout=self.timeout_s) as client:
                response = client.post(
                    f"{_OPENAI_BASE_URL}/embeddings",
                    headers=self._headers(),
                    json=payload,
                )
                latency_ms = (time.perf_counter() - started) * 1000.0
                status = response.status_code
                response.raise_for_status()
                body = response.json()
        except Exception as exc:  # noqa: BLE001 — bench は形式記録が目的
            latency_ms = (time.perf_counter() - started) * 1000.0
            status = getattr(getattr(exc, "response", None), "status_code", None)
            return CallRecord(
                api="embeddings",
                ok=False,
                latency_ms=latency_ms,
                error_kind="http_error",
                error_summary=_redacted_http_error(exc),
                http_status=status,
            )

        data = body.get("data")
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        total_tokens = int(usage.get("total_tokens") or usage.get("prompt_tokens") or 0)
        shape_ok = isinstance(data, list) and bool(data) and isinstance(data[0], dict)
        vector = data[0].get("embedding") if shape_ok else None
        if not isinstance(vector, list) or not vector:
            return CallRecord(
                api="embeddings",
                ok=False,
                latency_ms=latency_ms,
                error_kind="schema",
                error_summary="embeddings response missing data[0].embedding",
                http_status=status,
                total_tokens=total_tokens,
            )
        return CallRecord(
            api="embeddings",
            ok=True,
            latency_ms=latency_ms,
            total_tokens=total_tokens,
            http_status=status,
            response_shape=f"data[0].embedding:list[float] dims={len(vector)}",
        )

    def chat(self, prompt: str) -> CallRecord:
        system = (
            "You are a JSON-only assistant for gift semantic extraction. "
            'Respond with a single JSON object: {"concepts":[{"concept_code":"...","confidence":0.0,'
            '"input_intent":"neutral","evidence_texts":[]}]}'
        )
        payload = {
            "model": self.chat_model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 128,
        }
        started = time.perf_counter()
        try:
            with self._httpx.Client(timeout=self.timeout_s) as client:
                response = client.post(
                    f"{_OPENAI_BASE_URL}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
                latency_ms = (time.perf_counter() - started) * 1000.0
                status = response.status_code
                response.raise_for_status()
                body = response.json()
        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - started) * 1000.0
            status = getattr(getattr(exc, "response", None), "status_code", None)
            return CallRecord(
                api="chat.completions",
                ok=False,
                latency_ms=latency_ms,
                error_kind="http_error",
                error_summary=_redacted_http_error(exc),
                http_status=status,
            )

        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        choices = body.get("choices")
        content = None
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            message = choices[0].get("message")
            if isinstance(message, dict):
                content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            return CallRecord(
                api="chat.completions",
                ok=False,
                latency_ms=latency_ms,
                error_kind="schema",
                error_summary="chat response missing choices[0].message.content",
                http_status=status,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )
        return CallRecord(
            api="chat.completions",
            ok=True,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            http_status=status,
            response_shape="choices[0].message.content:str(json)",
        )

    def failure_probes(self) -> list[CallRecord]:
        """軽量な失敗形式観測（大量 429 誘発はしない）。"""
        probes: list[CallRecord] = []
        # 存在しないモデル名で 4xx を観測（課金ほぼなし）
        payload = {
            "model": "tv005-invalid-model-name-do-not-use",
            "input": "probe",
            "dimensions": _EMBEDDING_DIMENSIONS,
        }
        started = time.perf_counter()
        try:
            with self._httpx.Client(timeout=self.timeout_s) as client:
                response = client.post(
                    f"{_OPENAI_BASE_URL}/embeddings",
                    headers=self._headers(),
                    json=payload,
                )
                latency_ms = (time.perf_counter() - started) * 1000.0
                status = response.status_code
                if status < 400:
                    probes.append(
                        CallRecord(
                            api="embeddings",
                            ok=False,
                            latency_ms=latency_ms,
                            error_kind="unexpected_success",
                            error_summary=f"expected 4xx for invalid model, got {status}",
                            http_status=status,
                        )
                    )
                else:
                    # body は読まず status のみ記録
                    probes.append(
                        CallRecord(
                            api="embeddings",
                            ok=False,
                            latency_ms=latency_ms,
                            error_kind="invalid_model",
                            error_summary=(
                                f"HTTPStatusError status={status} "
                                "(body redacted for bench safety)"
                            ),
                            http_status=status,
                            response_shape="error object (type/code/message; body not logged)",
                        )
                    )
        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - started) * 1000.0
            status = getattr(getattr(exc, "response", None), "status_code", None)
            probes.append(
                CallRecord(
                    api="embeddings",
                    ok=False,
                    latency_ms=latency_ms,
                    error_kind="http_error",
                    error_summary=_redacted_http_error(exc),
                    http_status=status,
                )
            )
        return probes


def run_bench(
    *,
    mode: str,
    iterations: int,
    warmup: int,
    embedding_model: str,
    chat_model: str,
    probe_failures: bool,
) -> BenchResult:
    measured_at = datetime.now(timezone.utc).isoformat()
    result = BenchResult(
        mode=mode,
        embedding_model=embedding_model,
        chat_model=chat_model,
        iterations=iterations,
        warmup=warmup,
        measured_at_utc=measured_at,
    )

    if mode == "mock":
        client: MockOpenAiClient | SecretsOpenAiClient = MockOpenAiClient()
        result.notes.append("mock: HTTP 非実行。成功パスと失敗形式はローカル再現。")
    else:
        client = SecretsOpenAiClient(
            embedding_model=embedding_model,
            chat_model=chat_model,
            timeout_s=_TIMEOUT_S,
            api_key=_require_api_key(),
        )
        result.notes.append(
            "secrets: OPENAI_API_KEY を env からのみ使用。キー実値は出力しない。"
        )

    total_rounds = warmup + iterations
    for i in range(total_rounds):
        is_warmup = i < warmup
        emb = client.embedding(_SAMPLE_EMBED_TEXT)
        chat = client.chat(_SAMPLE_CHAT_PROMPT)
        if is_warmup:
            continue
        result.embedding_calls.append(emb)
        result.chat_calls.append(chat)
        if emb.ok:
            result.embedding_latencies_ms.append(emb.latency_ms)
        if chat.ok:
            result.chat_latencies_ms.append(chat.latency_ms)

    if probe_failures:
        if mode == "mock":
            assert isinstance(client, MockOpenAiClient)
            result.failure_probes = client.failure_probes()
        else:
            assert isinstance(client, SecretsOpenAiClient)
            result.failure_probes = client.failure_probes()
            result.notes.append(
                "failure probe: invalid model による 4xx を 1 回のみ観測。"
                " rate limit 大量誘発は未実施（Human 承認が必要）。"
            )
    else:
        result.notes.append("failure probe スキップ（--probe-failures 未指定）。")

    return result


def _write_summary_md(report: dict[str, Any], path: Path) -> None:
    emb = report["embedding"]["latency"]
    chat = report["chat"]["latency"]
    cost = report["cost_estimate_usd"]
    lines = [
        "# TV-005 OpenAI connectivity bench summary",
        "",
        f"- mode: `{report['mode']}`",
        f"- measured_at_utc: `{report['measured_at_utc']}`",
        f"- embedding_model: `{report['embedding_model']}`",
        f"- chat_model: `{report['chat_model']}`",
        f"- iterations: {report['iterations']} (warmup={report['warmup']})",
        "",
        "## Latency",
        "",
        "| API | success | p50 (ms) | p95 (ms) | max (ms) |",
        "| --- | ------- | -------- | -------- | -------- |",
        (
            f"| embeddings | {report['embedding']['success_count']} | "
            f"{emb['p50_ms']} | {emb['p95_ms']} | {emb['max_ms']} |"
        ),
        (
            f"| chat.completions | {report['chat']['success_count']} | "
            f"{chat['p50_ms']} | {chat['p95_ms']} | {chat['max_ms']} |"
        ),
        "",
        "## Tokens / cost estimate",
        "",
        f"- embedding tokens: {report['embedding']['token_total']}",
        (
            f"- chat tokens: prompt={report['chat']['prompt_tokens']} "
            f"completion={report['chat']['completion_tokens']}"
        ),
        f"- estimated USD (list price): total={cost['total_usd']}",
        "",
        "## Failure probes",
        "",
    ]
    probes = report.get("failure_probes") or []
    if not probes:
        lines.append("- (none)")
    else:
        lines.append("| api | http_status | error_kind | summary |")
        lines.append("| --- | ----------- | ---------- | ------- |")
        for probe in probes:
            lines.append(
                f"| {probe['api']} | {probe.get('http_status')} | "
                f"{probe.get('error_kind')} | {probe.get('error_summary')} |"
            )
    lines.extend(["", "## Notes", ""])
    for note in report.get("notes") or []:
        lines.append(f"- {note}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TV-005 OpenAI connectivity bench")
    parser.add_argument("--mode", choices=("mock", "secrets"), required=True)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--warmup", type=int, default=0)
    parser.add_argument("--embedding-model", default=_DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--chat-model", default=_DEFAULT_CHAT_MODEL)
    parser.add_argument(
        "--probe-failures",
        action="store_true",
        help="失敗形式を軽量観測（mock はローカル再現、secrets は invalid model 1 回）",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("../../scripts/perf/output-tv005"),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.iterations < 1:
        print("--iterations は 1 以上が必要です", file=sys.stderr)
        return 2
    if args.warmup < 0:
        print("--warmup は 0 以上が必要です", file=sys.stderr)
        return 2

    result = run_bench(
        mode=args.mode,
        iterations=args.iterations,
        warmup=args.warmup,
        embedding_model=args.embedding_model,
        chat_model=args.chat_model,
        probe_failures=args.probe_failures,
    )
    report = result.to_report()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "report.json"
    md_path = output_dir / "summary.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_summary_md(report, md_path)

    emb = report["embedding"]["latency"]
    chat = report["chat"]["latency"]
    print(
        f"TV-005 mode={report['mode']} "
        f"embed_p95={emb['p95_ms']}ms chat_p95={chat['p95_ms']}ms "
        f"cost_usd≈{report['cost_estimate_usd']['total_usd']} "
        f"-> {json_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
