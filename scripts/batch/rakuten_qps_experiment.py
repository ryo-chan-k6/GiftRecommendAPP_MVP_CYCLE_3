#!/usr/bin/env python3
"""Rakuten QPS pattern experiment (local / WSL only).

Runs a fixed sequence (genre → ranking → item_search×2) at several
min-interval settings and records success / 429 counts.

Safety:
  - Requires --live-rakuten
  - Requires RAKUTEN_EXPECTED_EGRESS_IP match (same as live verify)
  - Never prints secret values
  - Does not intentionally aim for 429; patterns escalate gradually
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_EGRESS_IP_LOOKUP_URL = "https://api.ipify.org"
_HARD_CAP_QPS = 10.0


def _mask(value: str | None) -> str:
    if value is None or value.strip() == "":
        return "(empty)"
    if len(value) <= 8:
        return "***REDACTED***"
    return f"{value[:2]}***REDACTED***{value[-2:]}"


def _fetch_egress_ip(*, timeout_seconds: float = 5.0) -> str:
    request = urllib.request.Request(
        _EGRESS_IP_LOOKUP_URL,
        headers={"User-Agent": "gift-reco-rakuten-qps-experiment/1.0"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8").strip()
    if not body:
        raise RuntimeError("egress IP lookup returned empty body")
    return body


def _require_egress_ip_match() -> None:
    expected = (os.environ.get("RAKUTEN_EXPECTED_EGRESS_IP") or "").strip()
    if not expected:
        raise RuntimeError("RAKUTEN_EXPECTED_EGRESS_IP is required")
    observed = _fetch_egress_ip()
    if observed != expected:
        raise RuntimeError(
            "Egress IP mismatch: "
            f"expected={_mask(expected)} observed={_mask(observed)}"
        )


@dataclass
class CallOutcome:
    name: str
    ok: bool
    elapsed_ms: float
    error_code: str | None = None
    is_rate_limited: bool = False


@dataclass
class PatternTrial:
    target_qps: float
    min_interval_ms: int
    trial_index: int
    outcomes: list[CallOutcome] = field(default_factory=list)
    wall_ms: float = 0.0

    @property
    def success_count(self) -> int:
        return sum(1 for o in self.outcomes if o.ok)

    @property
    def failure_count(self) -> int:
        return sum(1 for o in self.outcomes if not o.ok)

    @property
    def rate_limited_count(self) -> int:
        return sum(1 for o in self.outcomes if o.is_rate_limited)


def _run_call(name: str, fn) -> CallOutcome:
    started = time.perf_counter()
    try:
        fn()
        return CallOutcome(
            name=name,
            ok=True,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )
    except Exception as exc:  # noqa: BLE001
        code = getattr(exc, "code", None)
        code_s = str(code) if code is not None else None
        return CallOutcome(
            name=name,
            ok=False,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
            error_code=code_s,
            is_rate_limited=code_s == "GRS-EXT-102",
        )


def _interval_ms_for_qps(qps: float) -> int:
    if qps <= 0 or qps > _HARD_CAP_QPS:
        raise ValueError(f"qps must be in (0, {_HARD_CAP_QPS}]")
    return int(math.ceil(1000.0 / qps))


def run_trial(
    *,
    client: Any,
    target_qps: float,
    trial_index: int,
    genre_id: str,
    keyword: str,
    hits: int,
) -> PatternTrial:
    interval_ms = _interval_ms_for_qps(target_qps)
    interval_s = interval_ms / 1000.0
    trial = PatternTrial(
        target_qps=target_qps,
        min_interval_ms=interval_ms,
        trial_index=trial_index,
    )
    wall_started = time.perf_counter()

    calls = [
        ("genre", lambda: client.fetch_genre_raw(genre_id=genre_id)),
        (
            "ranking",
            lambda: client.fetch_ranking_raw(
                genre_id=genre_id, period="daily", page=1
            ),
        ),
        (
            "item_search_p1",
            lambda: client.fetch_item_search_raw(
                cursor_type="keyword",
                keyword=keyword,
                page=1,
                hits=hits,
            ),
        ),
        (
            "item_search_p2",
            lambda: client.fetch_item_search_raw(
                cursor_type="keyword",
                keyword=keyword,
                page=2,
                hits=hits,
            ),
        ),
    ]
    for i, (name, fn) in enumerate(calls):
        trial.outcomes.append(_run_call(name, fn))
        if i < len(calls) - 1:
            time.sleep(interval_s)

    trial.wall_ms = (time.perf_counter() - wall_started) * 1000.0
    return trial


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rakuten QPS pattern experiment")
    parser.add_argument("--live-rakuten", action="store_true", required=False)
    parser.add_argument(
        "--qps-list",
        default="1,2,3,4,5,6,8",
        help="Comma-separated target QPS values (ascending recommended).",
    )
    parser.add_argument("--trials", type=int, default=2, help="Trials per QPS.")
    parser.add_argument(
        "--cooldown-sec",
        type=float,
        default=8.0,
        help="Cooldown between trials/patterns.",
    )
    parser.add_argument("--genre-id", default="0")
    parser.add_argument("--keyword", default="ギフト")
    parser.add_argument("--hits", type=int, default=3)
    parser.add_argument(
        "--output",
        default="ai-logs/experiments/2026-07-24-rakuten-qps-pattern-results.json",
    )
    args = parser.parse_args(argv)

    if not args.live_rakuten:
        print("Pass --live-rakuten explicitly. No HTTP request was made.", file=sys.stderr)
        return 3

    try:
        _require_egress_ip_match()
    except (RuntimeError, urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"{exc}. No Rakuten HTTP request was made.", file=sys.stderr)
        return 2

    application_id = os.environ.get("RAKUTEN_APPLICATION_ID")
    access_key = os.environ.get("RAKUTEN_ACCESS_KEY")
    if not application_id or not access_key:
        print(
            "RAKUTEN_APPLICATION_ID and RAKUTEN_ACCESS_KEY are required.",
            file=sys.stderr,
        )
        return 2

    qps_values = [float(x.strip()) for x in args.qps_list.split(",") if x.strip()]
    for q in qps_values:
        _interval_ms_for_qps(q)

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "batch" / "src"))
    from batch.infrastructure.rakuten import HttpRakutenApiClient  # noqa: E402

    client = HttpRakutenApiClient(
        application_id=application_id,
        access_key=access_key,
    )

    hits = max(1, min(args.hits, 30))
    trials: list[PatternTrial] = []
    started_at = datetime.now(timezone.utc).isoformat()

    print(
        f"experiment start qps_list={qps_values} trials={args.trials} "
        f"cooldown={args.cooldown_sec}s calls_per_trial=4"
    )

    for qps in qps_values:
        for trial_index in range(1, args.trials + 1):
            print(
                f"run qps={qps:g} trial={trial_index}/{args.trials} "
                f"interval_ms={_interval_ms_for_qps(qps)} ..."
            )
            trial = run_trial(
                client=client,
                target_qps=qps,
                trial_index=trial_index,
                genre_id=args.genre_id,
                keyword=args.keyword,
                hits=hits,
            )
            trials.append(trial)
            print(
                f"  result success={trial.success_count}/{len(trial.outcomes)} "
                f"rl={trial.rate_limited_count} wall_ms={trial.wall_ms:.0f}"
            )
            for o in trial.outcomes:
                mark = "ok" if o.ok else (o.error_code or "fail")
                print(f"    - {o.name}: {mark} ({o.elapsed_ms:.0f}ms)")
            time.sleep(args.cooldown_sec)

    # Aggregate by QPS
    by_qps: dict[str, dict[str, Any]] = {}
    for trial in trials:
        key = f"{trial.target_qps:g}"
        bucket = by_qps.setdefault(
            key,
            {
                "target_qps": trial.target_qps,
                "min_interval_ms": trial.min_interval_ms,
                "trials": 0,
                "calls": 0,
                "success": 0,
                "failure": 0,
                "rate_limited": 0,
                "all_success_trials": 0,
            },
        )
        bucket["trials"] += 1
        bucket["calls"] += len(trial.outcomes)
        bucket["success"] += trial.success_count
        bucket["failure"] += trial.failure_count
        bucket["rate_limited"] += trial.rate_limited_count
        if trial.failure_count == 0:
            bucket["all_success_trials"] += 1

    for bucket in by_qps.values():
        calls = max(bucket["calls"], 1)
        bucket["success_rate"] = bucket["success"] / calls
        bucket["rate_limited_rate"] = bucket["rate_limited"] / calls
        bucket["stable"] = (
            bucket["rate_limited"] == 0 and bucket["all_success_trials"] == bucket["trials"]
        )

    # Recommendation: highest QPS that is stable across all trials
    stable_qps = [
        b["target_qps"] for b in by_qps.values() if b["stable"]
    ]
    recommended_qps = max(stable_qps) if stable_qps else None
    # conservative pick: if multiple, prefer one step below hard edge
    recommended_note = (
        "highest QPS with 0 rate-limits and all trials fully successful"
        if recommended_qps is not None
        else "no fully stable pattern; prefer lowest tested QPS and backoff"
    )

    report = {
        "experiment_id": "2026-07-24-rakuten-qps-pattern",
        "issue": 1603,
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "constraints": {
            "hard_cap_qps": _HARD_CAP_QPS,
            "previous_target_qps": 8,
            "calls_per_trial": 4,
            "call_sequence": ["genre", "ranking", "item_search_p1", "item_search_p2"],
            "cooldown_sec": args.cooldown_sec,
            "trials_per_qps": args.trials,
        },
        "credentials": {
            "RAKUTEN_APPLICATION_ID_masked": _mask(application_id),
            "RAKUTEN_ACCESS_KEY_present": True,
        },
        "trials": [asdict(t) for t in trials],
        "aggregate_by_qps": by_qps,
        "recommendation": {
            "recommended_operational_qps": recommended_qps,
            "note": recommended_note,
            "inference": (
                "Treat recommended value as operational target ceiling for sustained "
                "sequential batch calls on this egress IP. Keep hard cap at 10. "
                "MOD-BATCH-008 should still implement backoff on 429."
            ),
        },
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    print(
        "recommended_operational_qps="
        f"{recommended_qps if recommended_qps is not None else 'none'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
