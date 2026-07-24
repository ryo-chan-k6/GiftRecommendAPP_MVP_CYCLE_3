#!/usr/bin/env python3
"""Minimal Rakuten live connectivity probe (TV-001〜003 / Issue #1603).

Usage (from repo root or apps/batch):

  set -a && source /path/to/.env && set +a
  cd apps/batch
  uv run python ../../scripts/batch/rakuten_live_verify.py --live-rakuten \\
    --output-dir ../../scripts/batch/output-rakuten-live

Safety:
  - Refuses to call the network without --live-rakuten
  - Never prints secret values
  - Limits to a few requests (genre / ranking / item_search + optional error probe)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def _mask(value: str | None) -> str:
    if value is None or value.strip() == "":
        return "(empty)"
    if len(value) <= 8:
        return "***REDACTED***"
    return f"{value[:2]}***REDACTED***{value[-2:]}"


def _top_keys(payload: dict[str, Any], *, limit: int = 20) -> list[str]:
    return sorted(payload.keys())[:limit]


def _nested_keys(payload: dict[str, Any], path: str) -> list[str]:
    node: Any = payload
    for part in path.split("."):
        if not isinstance(node, dict):
            return []
        node = node.get(part)
    if isinstance(node, dict):
        return sorted(node.keys())
    if isinstance(node, list) and node and isinstance(node[0], dict):
        first = node[0]
        # Rakuten often wraps as {"Item": {...}}
        if "Item" in first and isinstance(first["Item"], dict):
            return sorted(first["Item"].keys())
        return sorted(first.keys())
    return []


@dataclass
class CallResult:
    name: str
    ok: bool
    elapsed_ms: float
    error_type: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    top_level_keys: list[str] = field(default_factory=list)
    nested_field_keys: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)


def _run_call(name: str, fn, *, nested_path: str | None = None) -> CallResult:
    started = time.perf_counter()
    try:
        payload = fn()
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if not isinstance(payload, dict):
            return CallResult(
                name=name,
                ok=False,
                elapsed_ms=elapsed_ms,
                error_type="TypeError",
                error_message="response is not a dict",
            )
        result = CallResult(
            name=name,
            ok=True,
            elapsed_ms=elapsed_ms,
            top_level_keys=_top_keys(payload),
        )
        if nested_path:
            result.nested_field_keys = _nested_keys(payload, nested_path)
        # light counts without dumping bodies
        for key in ("Items", "children", "parents", "genres", "GenreInformation"):
            val = payload.get(key)
            if isinstance(val, list):
                result.counts[key] = len(val)
        if "pageCount" in payload and isinstance(payload["pageCount"], int):
            result.counts["pageCount"] = payload["pageCount"]
        if "hits" in payload and isinstance(payload["hits"], int):
            result.counts["hits"] = payload["hits"]
        if "count" in payload and isinstance(payload["count"], int):
            result.counts["count"] = payload["count"]
        return result
    except Exception as exc:  # noqa: BLE001 — probe records any failure shape
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        code = getattr(exc, "code", None)
        message = str(exc)
        # belt-and-suspenders: scrub env secrets if present in message
        for secret_name in ("RAKUTEN_APPLICATION_ID", "RAKUTEN_ACCESS_KEY"):
            secret = os.environ.get(secret_name)
            if secret and secret in message:
                message = message.replace(secret, _mask(secret))
        return CallResult(
            name=name,
            ok=False,
            elapsed_ms=elapsed_ms,
            error_type=type(exc).__name__,
            error_code=str(code) if code is not None else None,
            error_message=message,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rakuten live verify (explicit --live-rakuten only)")
    parser.add_argument(
        "--live-rakuten",
        action="store_true",
        help="Required to perform real HTTP calls.",
    )
    parser.add_argument(
        "--genre-id",
        default="0",
        help="Genre ID for genre/ranking probes (default: 0 = root).",
    )
    parser.add_argument(
        "--keyword",
        default="ギフト",
        help="Keyword for item_search probe (default: ギフト).",
    )
    parser.add_argument(
        "--hits",
        type=int,
        default=3,
        help="item_search hits (max 30, default 3).",
    )
    parser.add_argument(
        "--probe-invalid",
        action="store_true",
        help="Also probe one invalid genre request for error shape.",
    )
    parser.add_argument(
        "--output-dir",
        default="scripts/batch/output-rakuten-live",
        help="Directory for report.json / summary.md (gitignored pattern).",
    )
    args = parser.parse_args(argv)

    if not args.live_rakuten:
        print(
            "Refusing network calls: pass --live-rakuten explicitly. "
            "No HTTP request was made.",
            file=sys.stderr,
        )
        return 3

    application_id = os.environ.get("RAKUTEN_APPLICATION_ID")
    access_key = os.environ.get("RAKUTEN_ACCESS_KEY")
    if not application_id:
        print(
            "RAKUTEN_APPLICATION_ID is required in the environment. No HTTP request was made.",
            file=sys.stderr,
        )
        return 2

    # Import after live check so --help / dry refusal stays lightweight.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "batch" / "src"))
    from batch.infrastructure.rakuten import HttpRakutenApiClient  # noqa: E402

    # accessKey 未設定でも観測するため、空文字で Http client を直接構築する。
    # create_rakuten_client(live=True) は両方が揃わないと Scaffold に落ちる。
    client = HttpRakutenApiClient(
        application_id=application_id,
        access_key=access_key or "",
    )

    hits = max(1, min(args.hits, 30))
    calls: list[CallResult] = []

    calls.append(
        _run_call(
            "genre.fetch_genre_raw",
            lambda: client.fetch_genre_raw(genre_id=args.genre_id),
            nested_path="current",
        )
    )
    # small pause to reduce rate-limit risk
    time.sleep(0.4)
    calls.append(
        _run_call(
            "ranking.fetch_ranking_raw",
            lambda: client.fetch_ranking_raw(genre_id=args.genre_id, period="daily", page=1),
            nested_path="Items",
        )
    )
    time.sleep(0.4)
    calls.append(
        _run_call(
            "item_search.fetch_item_search_raw",
            lambda: client.fetch_item_search_raw(
                cursor_type="keyword",
                keyword=args.keyword,
                page=1,
                hits=hits,
            ),
            nested_path="Items",
        )
    )
    time.sleep(0.4)
    calls.append(
        _run_call(
            "item_search.page2",
            lambda: client.fetch_item_search_raw(
                cursor_type="keyword",
                keyword=args.keyword,
                page=2,
                hits=hits,
            ),
            nested_path="Items",
        )
    )

    if args.probe_invalid:
        time.sleep(0.4)
        calls.append(
            _run_call(
                "genre.invalid_genre_id",
                lambda: client.fetch_genre_raw(genre_id="not-a-genre"),
            )
        )

    for call in calls:
        if call.ok and not call.nested_field_keys and call.name.startswith("genre"):
            call.observations.append("current/children keys may be absent depending on genreId")
        if call.ok and call.counts.get("Items", 0) == 0 and "item_search" in call.name:
            call.observations.append("Items empty — keyword/genre may yield zero hits")

    report = {
        "task": "batch-external-api-rakuten-live-verify",
        "issue": 1603,
        "tv_mapping": {
            "genre": "TV-003",
            "ranking": "TV-002",
            "item_search": "TV-001",
        },
        "credentials": {
            "RAKUTEN_APPLICATION_ID_present": True,
            "RAKUTEN_ACCESS_KEY_present": bool(access_key),
            "RAKUTEN_APPLICATION_ID_masked": _mask(application_id),
            "RAKUTEN_ACCESS_KEY_masked": _mask(access_key),
        },
        "request_params": {
            "genre_id": args.genre_id,
            "keyword": args.keyword,
            "hits": hits,
            "probe_invalid": args.probe_invalid,
            "access_key_sent_empty": not bool(access_key),
        },
        "calls": [asdict(c) for c in calls],
        "summary": {
            "success_count": sum(1 for c in calls if c.ok),
            "failure_count": sum(1 for c in calls if not c.ok),
            "max_elapsed_ms": max((c.elapsed_ms for c in calls), default=0.0),
        },
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "report.json"
    summary_path = out_dir / "summary.md"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Rakuten live verify summary",
        "",
        f"- issue: #1603",
        f"- application_id: {_mask(application_id)}",
        f"- access_key_present: {bool(access_key)}",
        f"- success: {report['summary']['success_count']} / {len(calls)}",
        "",
        "| name | ok | ms | error_code | notes |",
        "| ---- | -- | -- | ---------- | ----- |",
    ]
    for c in calls:
        note = c.error_message or ",".join(c.observations) or ""
        note = note.replace("|", "/")[:120]
        lines.append(
            f"| {c.name} | {c.ok} | {c.elapsed_ms:.1f} | {c.error_code or ''} | {note} |"
        )
    lines.append("")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {report_path}")
    print(f"Wrote {summary_path}")
    print(
        f"success={report['summary']['success_count']} "
        f"failure={report['summary']['failure_count']} "
        f"access_key_present={bool(access_key)}"
    )
    # exit 0 if at least one success; 1 if all failed (still wrote report)
    return 0 if report["summary"]["success_count"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
