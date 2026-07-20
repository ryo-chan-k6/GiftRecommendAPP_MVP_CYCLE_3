#!/usr/bin/env bash
# summarize-ui-e2e-soak.sh
#
# UI E2E required 昇格前の soak（安定性観測）進捗を集計する。
# 正本の基準: ai-logs/human-decisions/2026-07-20-ui-e2e-required-promotion-plan.md
#   - 2 週間 かつ 10 PR で flake 0
#   - required 対象想定チェック名: "UI E2E gate"
#
# 使い方:
#   ./scripts/ops/summarize-ui-e2e-soak.sh
#   ./scripts/ops/summarize-ui-e2e-soak.sh --since 2026-07-19T16:37:25Z --limit 80
#   ./scripts/ops/summarize-ui-e2e-soak.sh --markdown
#
# 必要: gh CLI / python3（repo 読み取り権限）
set -euo pipefail

REPO="${GITHUB_REPOSITORY:-ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3}"
WORKFLOW="test-ui-e2e.yml"
# soak 開始（推奨）: Epic #1472 merge（ui-e2e-gate 導入）
SINCE_DEFAULT="2026-07-19T16:37:25Z"
SINCE="${SINCE_DEFAULT}"
LIMIT=80
MARKDOWN=0
TARGET_PR_COUNT=10
SOAK_DAYS=14

usage() {
  cat <<'EOF'
Usage: summarize-ui-e2e-soak.sh [--since ISO8601] [--limit N] [--markdown] [--repo owner/repo]

Aggregates GitHub Actions runs of test-ui-e2e.yml for required-promotion soak.

Counts unique PRs where heavy job "UI E2E (S1)" finished with
success/failure/timed_out (skipped/cancelled excluded).
Flake (simple): failure/timed_out of "UI E2E (S1)" or "UI E2E gate",
excluding cancelled context (run/Decide/S1 cancelled by concurrency).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --since) SINCE="${2:-}"; shift 2 ;;
    --limit) LIMIT="${2:-}"; shift 2 ;;
    --markdown) MARKDOWN=1; shift ;;
    --repo) REPO="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "error: unknown arg: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if ! command -v gh >/dev/null 2>&1; then
  echo "error: gh CLI is required" >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 is required" >&2
  exit 1
fi

export REPO WORKFLOW SINCE LIMIT MARKDOWN TARGET_PR_COUNT SOAK_DAYS

python3 - <<'PY'
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.environ["REPO"]
WORKFLOW = os.environ["WORKFLOW"]
SINCE = os.environ["SINCE"]
LIMIT = int(os.environ["LIMIT"])
MARKDOWN = os.environ["MARKDOWN"] == "1"
TARGET_PR_COUNT = int(os.environ["TARGET_PR_COUNT"])
SOAK_DAYS = int(os.environ["SOAK_DAYS"])


def gh_json(args: list[str]):
    cmd = ["gh", *args, "--repo", REPO]
    out = subprocess.check_output(cmd, text=True)
    return json.loads(out)


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def extract_pr(title: str) -> str:
    m = re.search(r"\b(\d+)/merge\b", title or "")
    if m:
        return m.group(1)
    m = re.search(r"#(\d+)", title or "")
    return m.group(1) if m else ""


def is_fail(conclusion: str | None) -> bool:
    return conclusion in {"failure", "timed_out"}


def is_cancelled_context(conclusion: str, decide: str, s1: str) -> bool:
    """concurrency cancel-in-progress 等。flake から除外する。"""
    return conclusion == "cancelled" or decide == "cancelled" or s1 == "cancelled"


since_dt = parse_iso(SINCE)
now = datetime.now(timezone.utc)
elapsed_days = round((now - since_dt).total_seconds() / 86400, 1)
remaining_days = max(0.0, round(SOAK_DAYS - elapsed_days, 1))

runs = gh_json(
    [
        "run",
        "list",
        "--workflow",
        WORKFLOW,
        "--limit",
        str(LIMIT),
        "--json",
        "databaseId,conclusion,event,displayTitle,createdAt,headBranch,url,status",
    ]
)
runs = [r for r in runs if parse_iso(r["createdAt"]) >= since_dt]

rows = []
for r in runs:
    run_id = r["databaseId"]
    try:
        detail = gh_json(["run", "view", str(run_id), "--json", "jobs"])
    except subprocess.CalledProcessError:
        detail = {"jobs": []}
    jobs = {j.get("name"): j.get("conclusion") for j in detail.get("jobs") or []}
    s1 = jobs.get("UI E2E (S1)") or ""
    gate = jobs.get("UI E2E gate") or ""
    decide = jobs.get("Decide whether to run UI E2E") or ""
    run_conclusion = r.get("conclusion") or "in_progress"
    # cancelled は「実行サンプル」にも「flake」にも含めない
    s1_executed = s1 in {"success", "failure", "timed_out"}
    title = r.get("displayTitle") or ""
    rows.append(
        {
            "id": run_id,
            "createdAt": r.get("createdAt"),
            "event": r.get("event"),
            "conclusion": run_conclusion,
            "branch": r.get("headBranch") or "",
            "title": title,
            "url": r.get("url") or "",
            "pr": extract_pr(title),
            "decide": decide,
            "s1": s1,
            "gate": gate,
            "s1_executed": s1_executed,
            "cancelled_context": is_cancelled_context(run_conclusion, decide, s1),
        }
    )

s1_rows = [x for x in rows if x["s1_executed"]]
unique_prs = sorted({int(x["pr"]) for x in s1_rows if x["pr"].isdigit()})
s1_fail = [x for x in s1_rows if is_fail(x["s1"])]
# concurrency cancel で gate が failure になるケースは flake に含めない
gate_fail = [
    x
    for x in rows
    if is_fail(x["gate"]) and not x["cancelled_context"]
]
flake = bool(s1_fail or gate_fail)
pr_count = len(unique_prs)
pr_remaining = max(TARGET_PR_COUNT - pr_count, 0)

if elapsed_days >= SOAK_DAYS and pr_count >= TARGET_PR_COUNT and not flake:
    status = "READY FOR HUMAN required-promotion review"
elif flake:
    status = "NOT READY (flake detected)"
else:
    status = f"IN PROGRESS (need days>={SOAK_DAYS} and PRs>={TARGET_PR_COUNT} and flake=0)"

if MARKDOWN:
    print("## 自動集計スナップショット")
    print()
    print("| 項目 | 値 |")
    print("| ---- | ---- |")
    print(f"| 集計日時 (UTC) | {now.strftime('%Y-%m-%dT%H:%M:%SZ')} |")
    print(f"| since | `{SINCE}` |")
    print(f"| 経過日数 | {elapsed_days} / 目標 {SOAK_DAYS} |")
    print(f"| 残日数目安 | {remaining_days} |")
    print(f"| 総 run 数 | {len(rows)} |")
    print(f"| schedule | {sum(1 for x in rows if x['event']=='schedule')} |")
    print(f"| pull_request | {sum(1 for x in rows if x['event']=='pull_request')} |")
    print(f"| workflow_dispatch | {sum(1 for x in rows if x['event']=='workflow_dispatch')} |")
    print(
        f"| S1 実行 run | {len(s1_rows)}"
        f"（success={sum(1 for x in s1_rows if x['s1']=='success')}"
        f" / fail={len(s1_fail)}"
        f" / cancelled={sum(1 for x in s1_rows if x['s1']=='cancelled')}） |"
    )
    print(f"| gate fail run | {len(gate_fail)} |")
    print(f"| S1 実行ユニーク PR 数 | {pr_count} / {TARGET_PR_COUNT} |")
    print(f"| PR 一覧 | `{unique_prs}` |")
    print(f"| flake（簡易） | {str(flake).lower()} |")
    print(f"| 判定ヒント | {status} |")
    print()
    print("```bash")
    print(f"./scripts/ops/summarize-ui-e2e-soak.sh --since {SINCE} --markdown")
    print("```")
    print()
    print("### runs（新しい順）")
    print()
    print("| createdAt | event | PR | S1 | gate | run | URL |")
    print("| --------- | ----- | -- | -- | ---- | --- | --- |")
    for x in sorted(rows, key=lambda r: r["createdAt"], reverse=True):
        pr = x["pr"] or "-"
        s1 = x["s1"] or ("skipped" if not x["s1_executed"] else "-")
        gate = x["gate"] or "-"
        print(
            f"| {x['createdAt']} | {x['event']} | {pr} | {s1} | {gate} | {x['conclusion']} | {x['url']} |"
        )
    sys.exit(0)

print("=== UI E2E soak summary ===")
print(f"repo: {REPO}")
print(f"workflow: {WORKFLOW}")
print(f"since: {SINCE} (recommended: #1472 merge / ui-e2e-gate)")
print(f"criteria: {SOAK_DAYS} days AND {TARGET_PR_COUNT} PRs with flake 0")
print(f"elapsed_days: {elapsed_days} / remaining_days(min): {remaining_days}")
print()
print(
    f"runs: total={len(rows)} "
    f"schedule={sum(1 for x in rows if x['event']=='schedule')} "
    f"pull_request={sum(1 for x in rows if x['event']=='pull_request')} "
    f"dispatch={sum(1 for x in rows if x['event']=='workflow_dispatch')}"
)
print(
    f"S1 executed: {len(s1_rows)} "
    f"(success={sum(1 for x in s1_rows if x['s1']=='success')} "
    f"fail={len(s1_fail)} "
    f"cancelled={sum(1 for x in s1_rows if x['s1']=='cancelled')})"
)
print(f"gate fail runs: {len(gate_fail)}")
print(f"unique PRs with S1 executed: {pr_count}/{TARGET_PR_COUNT} (remaining={pr_remaining})")
print(f"PR list: {unique_prs}")
print(f"flake: {str(flake).lower()}")
print()
print("--- judgment hint (not auto-decision) ---")
print(f"status: {status}")
print()
print("=== runs (newest first) ===")
for x in sorted(rows, key=lambda r: r["createdAt"], reverse=True):
    print(
        f"{x['createdAt']} event={x['event']} pr={x['pr'] or '-'} "
        f"s1_exec={int(x['s1_executed'])} s1={x['s1'] or '-'} gate={x['gate'] or '-'} "
        f"run={x['conclusion']} {x['url']}"
    )
PY
