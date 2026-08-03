#!/usr/bin/env bash
# ジャンル地図キャンペーン（BATCH-001 BFS）共通関数
# 正本: docs/15_運用・改善/運用手順/ジャンル地図キャンペーン_BFS段階同期手順.md
# Decision: ai-logs/human-decisions/2026-08-03-batch-genre-map-campaign-ops-plan.md
# secret / .env 実値を echo しないこと。
# local_daily / local_weekly 親シェルは呼ばないこと。

set -euo pipefail

gmc_repo_root() {
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
  printf '%s\n' "${here}"
}

GMC_REPO_ROOT="$(gmc_repo_root)"
GMC_SCRIPTS_BATCH_DIR="${GMC_REPO_ROOT}/scripts/batch"
GMC_OUTPUT_DIR="${GMC_SCRIPTS_BATCH_DIR}/output-genre-map-campaign"
GMC_STATE_FILE="${GMC_OUTPUT_DIR}/campaign-state.json"
GMC_LOG_FILE="${GMC_OUTPUT_DIR}/campaign.log"

# Decision §2.3 hard / soft（80%）
GMC_HARD_ROWS="${GMC_HARD_ROWS:-100000}"
GMC_SOFT_ROWS="${GMC_SOFT_ROWS:-80000}"
GMC_HARD_API_CALLS="${GMC_HARD_API_CALLS:-100000}"
GMC_SOFT_API_CALLS="${GMC_SOFT_API_CALLS:-80000}"
GMC_HARD_RUNS="${GMC_HARD_RUNS:-5000}"
GMC_SOFT_RUNS="${GMC_SOFT_RUNS:-4000}"
GMC_HARD_RAW_BYTES="${GMC_HARD_RAW_BYTES:-$((5 * 1024 * 1024 * 1024))}"
GMC_SOFT_RAW_BYTES="${GMC_SOFT_RAW_BYTES:-$((4 * 1024 * 1024 * 1024))}"
GMC_HARD_QUEUE="${GMC_HARD_QUEUE:-50000}"
GMC_SOFT_QUEUE="${GMC_SOFT_QUEUE:-40000}"

GMC_MAX_GENRE_IDS_PER_RUN="${GMC_MAX_GENRE_IDS_PER_RUN:-20}"
GMC_ROOT_ID="${GMC_ROOT_ID:-0}"
GMC_CAMPAIGN_MAX_QPS="${GMC_CAMPAIGN_MAX_QPS:-1}"
GMC_DB_CONTAINER="${GMC_DB_CONTAINER:-supabase_db_gift-reco-local}"

gmc_mkdirs() {
  mkdir -p "${GMC_OUTPUT_DIR}"
}

gmc_log() {
  local level="$1"
  shift
  local ts
  ts="$(date -Iseconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z')"
  printf '%s [%s] %s\n' "${ts}" "${level}" "$*" | tee -a "${GMC_LOG_FILE}" >&2
}

gmc_die() {
  gmc_log ERROR "$@"
  exit 1
}

gmc_load_dotenv_if_present() {
  local env_file="${GMC_REPO_ROOT}/.env"
  if [[ -f "${env_file}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${env_file}"
    set +a
    gmc_log INFO "loaded dotenv from repo root (values not logged)"
  else
    gmc_log INFO "no .env at repo root (continuing with process env)"
  fi
}

gmc_default_state_json() {
  cat <<EOF
{
  "root_id": "${GMC_ROOT_ID}",
  "queue": ["${GMC_ROOT_ID}"],
  "seen": [],
  "expanded": [],
  "runs_completed": 0,
  "api_calls_estimated": 0,
  "soft_notified": {},
  "hard_stopped": false,
  "last_chunk": [],
  "updated_at": ""
}
EOF
}

gmc_ensure_state() {
  gmc_mkdirs
  if [[ ! -f "${GMC_STATE_FILE}" ]]; then
    gmc_default_state_json >"${GMC_STATE_FILE}"
    gmc_log INFO "initialized state: ${GMC_STATE_FILE}"
  fi
}

gmc_python() {
  if command -v python3 >/dev/null 2>&1; then
    python3 "$@"
  else
    python "$@"
  fi
}

# Print state fields via python (no secrets).
gmc_state_get() {
  local key="$1"
  GMC_STATE_FILE="${GMC_STATE_FILE}" gmc_python - "$key" <<'PY'
import json, os, sys
path = os.environ["GMC_STATE_FILE"]
key = sys.argv[1]
with open(path, encoding="utf-8") as f:
    data = json.load(f)
val = data.get(key)
if isinstance(val, (list, dict)):
    print(json.dumps(val, ensure_ascii=False))
elif val is None:
    print("")
else:
    print(val)
PY
}

gmc_state_update() {
  # stdin: python snippet that receives `data` dict and mutates it
  local snippet="$1"
  GMC_STATE_FILE="${GMC_STATE_FILE}" gmc_python -c "
import json, os
from datetime import datetime, timezone
path = os.environ['GMC_STATE_FILE']
with open(path, encoding='utf-8') as f:
    data = json.load(f)
${snippet}
data['updated_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write('\n')
"
}

gmc_db_available() {
  command -v docker >/dev/null 2>&1 || return 1
  docker inspect -f '{{.State.Running}}' "${GMC_DB_CONTAINER}" 2>/dev/null | grep -qx true
}

gmc_db_psql() {
  local sql="$1"
  docker exec "${GMC_DB_CONTAINER}" psql -U postgres -d postgres -At -c "${sql}"
}

gmc_metric_external_genre_rows() {
  if gmc_db_available; then
    gmc_db_psql "SELECT COUNT(*) FROM external_genre;" 2>/dev/null | tr -d '[:space:]' || echo "0"
  else
    echo "-1"
  fi
}

gmc_metric_raw_bytes_estimate() {
  # external_genre relation size as proxy for campaign raw growth (Decision soft/hard raw).
  if gmc_db_available; then
    gmc_db_psql "SELECT pg_total_relation_size('external_genre');" 2>/dev/null | tr -d '[:space:]' || echo "0"
  else
    echo "-1"
  fi
}

gmc_metric_queue_size() {
  gmc_state_get queue | gmc_python -c 'import json,sys; print(len(json.load(sys.stdin)))'
}

gmc_metric_runs() {
  gmc_state_get runs_completed
}

gmc_metric_api_calls() {
  gmc_state_get api_calls_estimated
}

gmc_gate_status() {
  # Prints TSV: knob current soft hard level(ok|soft|hard|unknown)
  local rows api runs raw queue
  rows="$(gmc_metric_external_genre_rows)"
  api="$(gmc_metric_api_calls)"
  runs="$(gmc_metric_runs)"
  raw="$(gmc_metric_raw_bytes_estimate)"
  queue="$(gmc_metric_queue_size)"

  gmc_python - "$rows" "$api" "$runs" "$raw" "$queue" \
    "${GMC_SOFT_ROWS}" "${GMC_HARD_ROWS}" \
    "${GMC_SOFT_API_CALLS}" "${GMC_HARD_API_CALLS}" \
    "${GMC_SOFT_RUNS}" "${GMC_HARD_RUNS}" \
    "${GMC_SOFT_RAW_BYTES}" "${GMC_HARD_RAW_BYTES}" \
    "${GMC_SOFT_QUEUE}" "${GMC_HARD_QUEUE}" <<'PY'
import sys

def level(cur, soft, hard):
    try:
        c = int(cur)
    except ValueError:
        return "unknown"
    if c < 0:
        return "unknown"
    if c >= int(hard):
        return "hard"
    if c >= int(soft):
        return "soft"
    return "ok"

args = sys.argv[1:]
rows, api, runs, raw, queue = args[0:5]
soft_rows, hard_rows = args[5:7]
soft_api, hard_api = args[7:9]
soft_runs, hard_runs = args[9:11]
soft_raw, hard_raw = args[11:13]
soft_q, hard_q = args[13:15]

rows_list = [
    ("max_external_genre_rows", rows, soft_rows, hard_rows),
    ("max_api_calls", api, soft_api, hard_api),
    ("max_runs", runs, soft_runs, hard_runs),
    ("max_raw_storage_bytes", raw, soft_raw, hard_raw),
    ("max_queue_size", queue, soft_q, hard_q),
]
for name, cur, soft, hard in rows_list:
    print(f"{name}\t{cur}\t{soft}\t{hard}\t{level(cur, soft, hard)}")
PY
}

gmc_any_hard() {
  gmc_gate_status | awk -F'\t' '$5=="hard"{found=1} END{exit found?0:1}'
}

gmc_soft_knobs() {
  gmc_gate_status | awk -F'\t' '$5=="soft"{print $1}'
}

# Slack hook: reuse slack-notify.cjs postSlackMessage when token+channel present.
# Never prints token / webhook. dry-run logs payload summary only.
gmc_slack_notify() {
  local level="$1"
  local title="$2"
  local summary="$3"
  local dry="${4:-0}"

  local token="${SLACK_BOT_TOKEN:-}"
  local channel="${SLACK_CAMPAIGN_CHANNEL:-${SLACK_OPS_CHANNEL:-}}"

  if [[ -z "${token}" || -z "${channel}" ]]; then
    gmc_log INFO "Slack skipped (SLACK_BOT_TOKEN / channel env unset). level=${level} title=${title}"
    gmc_log INFO "Slack summary (no secrets): ${summary}"
    return 0
  fi

  if [[ "${dry}" == "1" ]]; then
    gmc_log INFO "Slack dry-run (would post). level=${level} title=${title} channel=<set>"
    gmc_log INFO "Slack summary (no secrets): ${summary}"
    return 0
  fi

  local script="${GMC_REPO_ROOT}/.github/scripts/slack-notify.cjs"
  if [[ ! -f "${script}" ]]; then
    gmc_log WARN "slack-notify.cjs missing; Slack skipped"
    return 0
  fi

  SLACK_BOT_TOKEN="${token}" GMC_SLACK_CHANNEL="${channel}" \
  GMC_SLACK_LEVEL="${level}" GMC_SLACK_TITLE="${title}" GMC_SLACK_SUMMARY="${summary}" \
  node -e '
const path = require("path");
const slack = require(path.join(process.cwd(), ".github/scripts/slack-notify.cjs"));
(async () => {
  const text = slack.buildSlackText({
    level: process.env.GMC_SLACK_LEVEL,
    title: process.env.GMC_SLACK_TITLE,
    summary: process.env.GMC_SLACK_SUMMARY,
    fields: {
      Campaign: "batch-genre-map-campaign",
      Issue: "#1833 / Epic #1827",
    },
  });
  const result = await slack.postSlackMessage({
    token: process.env.SLACK_BOT_TOKEN,
    channel: process.env.GMC_SLACK_CHANNEL,
    text,
  });
  if (!result || result.ok === false) {
    console.error("Slack post failed (token not logged)");
    process.exitCode = 1;
  }
})().catch((err) => {
  console.error("Slack error:", err && err.message ? err.message : "unknown");
  process.exitCode = 1;
});
' >/dev/null
  local rc=$?
  if [[ $rc -ne 0 ]]; then
    gmc_log WARN "Slack post failed (details suppressed; secret not logged)"
  else
    gmc_log INFO "Slack notified: level=${level} title=${title}"
  fi
  return 0
}

gmc_take_chunk() {
  # Reads queue from state, returns up to N ids as comma-separated; updates state queue/seen/last_chunk
  local n="${1:-${GMC_MAX_GENRE_IDS_PER_RUN}}"
  GMC_STATE_FILE="${GMC_STATE_FILE}" GMC_CHUNK_N="${n}" gmc_python <<'PY'
import json, os
path = os.environ["GMC_STATE_FILE"]
n = int(os.environ["GMC_CHUNK_N"])
with open(path, encoding="utf-8") as f:
    data = json.load(f)
queue = [str(x) for x in data.get("queue") or []]
chunk = queue[:n]
rest = queue[n:]
seen = set(str(x) for x in data.get("seen") or [])
for x in chunk:
    seen.add(x)
data["queue"] = rest
data["seen"] = sorted(seen, key=lambda s: (len(s), s))
data["last_chunk"] = chunk
from datetime import datetime, timezone
data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(",".join(chunk))
PY
}

gmc_peek_chunk() {
  local n="${1:-${GMC_MAX_GENRE_IDS_PER_RUN}}"
  GMC_STATE_FILE="${GMC_STATE_FILE}" GMC_CHUNK_N="${n}" gmc_python <<'PY'
import json, os
path = os.environ["GMC_STATE_FILE"]
n = int(os.environ["GMC_CHUNK_N"])
with open(path, encoding="utf-8") as f:
    data = json.load(f)
queue = [str(x) for x in data.get("queue") or []]
print(",".join(queue[:n]))
PY
}

gmc_enqueue_ids() {
  # stdin: newline-separated genre ids to append (dedupe against seen+queue)
  GMC_STATE_FILE="${GMC_STATE_FILE}" gmc_python <<'PY'
import json, os, sys
path = os.environ["GMC_STATE_FILE"]
new_ids = [line.strip() for line in sys.stdin if line.strip()]
with open(path, encoding="utf-8") as f:
    data = json.load(f)
queue = [str(x) for x in data.get("queue") or []]
seen = set(str(x) for x in data.get("seen") or [])
expanded = set(str(x) for x in data.get("expanded") or [])
in_queue = set(queue)
added = []
for gid in new_ids:
    if gid in seen or gid in in_queue or gid in expanded:
        continue
    queue.append(gid)
    in_queue.add(gid)
    added.append(gid)
data["queue"] = queue
from datetime import datetime, timezone
data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(",".join(added))
PY
}

gmc_mark_expanded() {
  local ids_csv="$1"
  GMC_STATE_FILE="${GMC_STATE_FILE}" GMC_IDS="${ids_csv}" gmc_python <<'PY'
import json, os
path = os.environ["GMC_STATE_FILE"]
ids = [x for x in os.environ.get("GMC_IDS", "").split(",") if x]
with open(path, encoding="utf-8") as f:
    data = json.load(f)
expanded = set(str(x) for x in data.get("expanded") or [])
for i in ids:
    expanded.add(i)
data["expanded"] = sorted(expanded, key=lambda s: (len(s), s))
data["runs_completed"] = int(data.get("runs_completed") or 0) + 1
# Estimate: 1 API call per genre-id in chunk (parent fetch). Children come in same response.
data["api_calls_estimated"] = int(data.get("api_calls_estimated") or 0) + len(ids)
from datetime import datetime, timezone
data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
}

gmc_discover_children_from_db() {
  # After syncing parents, enqueue non-leaf children not yet expanded.
  # Uses: children of expanded parents that are is_leaf=false and not in expanded.
  if ! gmc_db_available; then
    gmc_log WARN "DB unavailable; cannot discover children for queue"
    return 0
  fi
  local sql
  sql="SELECT external_genre_id FROM external_genre WHERE is_leaf = false ORDER BY genre_level, external_genre_id;"
  local ids
  ids="$(gmc_db_psql "${sql}" 2>/dev/null || true)"
  if [[ -z "${ids}" ]]; then
    gmc_log INFO "no non-leaf genres in DB to enqueue"
    return 0
  fi
  local added
  added="$(printf '%s\n' "${ids}" | gmc_enqueue_ids)"
  if [[ -n "${added}" ]]; then
    gmc_log INFO "enqueued non-leaf candidates: ${added}"
  else
    gmc_log INFO "no new non-leaf candidates to enqueue"
  fi
}

gmc_print_gates() {
  echo "=== Capacity gates (Decision §2.3) ==="
  printf '%-28s %12s %12s %12s %8s\n' "knob" "current" "soft" "hard" "level"
  while IFS=$'\t' read -r name cur soft hard level; do
    printf '%-28s %12s %12s %12s %8s\n' "${name}" "${cur}" "${soft}" "${hard}" "${level}"
  done < <(gmc_gate_status)
}

gmc_build_leaf_cmd() {
  local genre_ids_csv="$1"
  local live="$2" # 0|1
  local job_run_id="$3"
  local qps="${GMC_CAMPAIGN_MAX_QPS}"

  # Leaf CLI only — never weekly/daily parent.
  # max_qps via RAKUTEN_MAX_QPS (genre_sync has no --max-qps CLI yet).
  local base="cd apps/batch && RAKUTEN_MAX_QPS=${qps} uv run python -m batch.application.genre_sync"
  base+=" --job-run-id ${job_run_id} --genre-ids ${genre_ids_csv}"
  if [[ "${live}" == "1" ]]; then
    base+=" --live-rakuten"
  fi
  printf '%s\n' "${base}"
}

gmc_generate_uuid() {
  if command -v uuidgen >/dev/null 2>&1; then
    uuidgen | tr '[:upper:]' '[:lower:]'
    return 0
  fi
  gmc_python -c 'import uuid; print(uuid.uuid4())'
}
