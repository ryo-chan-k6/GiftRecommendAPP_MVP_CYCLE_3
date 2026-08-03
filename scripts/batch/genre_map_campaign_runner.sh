#!/usr/bin/env bash
# ジャンル地図キャンペーン BATCH-001 BFS ラッパ
#
# 正本手順: docs/15_運用・改善/運用手順/ジャンル地図キャンペーン_BFS段階同期手順.md
# Decision: ai-logs/human-decisions/2026-08-03-batch-genre-map-campaign-ops-plan.md
#
# 禁止:
# - local_daily_orchestrator.sh / local_weekly_orchestrator.sh の呼び出し
# - AI による --live-rakuten 実行（live は Human のみ・明示フラグ必須）
# - secret / .env 実値のログ出力
# - 定常 crontab / GHA schedule 変更（本スクリプトは行わない）
#
# 既定は dry-run（計画・キュー・閾値表示のみ。楽天 HTTP なし）。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/genre_map_campaign_common.sh
source "${SCRIPT_DIR}/lib/genre_map_campaign_common.sh"

GMC_DRY_RUN=1
GMC_LIVE_RAKUTEN=0
GMC_I_AM_HUMAN=0
GMC_RESET_STATE=0
GMC_MAX_RUNS_THIS_INVOCATION=1
GMC_SKIP_DB_DISCOVER=0
GMC_SEED_QUEUE=""

usage() {
  cat <<'EOF'
Usage:
  ./scripts/batch/genre_map_campaign_runner.sh --dry-run [options]
  ./scripts/batch/genre_map_campaign_runner.sh --live-rakuten --i-am-human [options]

Options:
  --dry-run                 計画・キュー・閾値のみ（既定。楽天 HTTP なし）
  --live-rakuten            葉 BATCH-001 を live 実行（Human 専用・--i-am-human 必須）
  --i-am-human              Human 実行の明示確認（AI 実行パスでは付けない）
  --reset-state             campaign-state.json を root キューから初期化
  --max-runs-this-invocation N  この起動で実行する BATCH-001 Run 数上限（既定 1）
  --seed-queue IDS          カンマ区切りで初期キュー上書き（例: 0 または 0,100000）
  --skip-db-discover        Run 後の DB non-leaf enqueue をスキップ
  -h, --help                このヘルプ

Environment (values never logged):
  GMC_DB_CONTAINER          既定 supabase_db_gift-reco-local
  GMC_CAMPAIGN_MAX_QPS      既定 1（RAKUTEN_MAX_QPS に渡す）
  GMC_MAX_GENRE_IDS_PER_RUN 既定 20
  SLACK_BOT_TOKEN + SLACK_CAMPAIGN_CHANNEL（または SLACK_OPS_CHANNEL）
  hard/soft overrides: GMC_HARD_ROWS / GMC_SOFT_ROWS / ...

Notes:
  - weekly/daily 親シェルは呼ばない（葉 CLI のみ）
  - MVP fetch_plan 4ID（100000/100003/100004/100005）は置き換えない
  - AI Agent は --live-rakuten を付けないこと
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      GMC_DRY_RUN=1
      GMC_LIVE_RAKUTEN=0
      shift
      ;;
    --live-rakuten)
      GMC_LIVE_RAKUTEN=1
      GMC_DRY_RUN=0
      shift
      ;;
    --i-am-human)
      GMC_I_AM_HUMAN=1
      shift
      ;;
    --reset-state)
      GMC_RESET_STATE=1
      shift
      ;;
    --max-runs-this-invocation=*)
      GMC_MAX_RUNS_THIS_INVOCATION="${1#*=}"
      shift
      ;;
    --max-runs-this-invocation)
      GMC_MAX_RUNS_THIS_INVOCATION="${2:-}"
      shift 2
      ;;
    --seed-queue=*)
      GMC_SEED_QUEUE="${1#*=}"
      shift
      ;;
    --seed-queue)
      GMC_SEED_QUEUE="${2:-}"
      shift 2
      ;;
    --skip-db-discover)
      GMC_SKIP_DB_DISCOVER=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      gmc_die "unknown argument: $1 (see --help)"
      ;;
  esac
done

if [[ "${GMC_LIVE_RAKUTEN}" == "1" && "${GMC_DRY_RUN}" == "1" ]]; then
  gmc_die "--live-rakuten and --dry-run are mutually exclusive"
fi

if [[ "${GMC_LIVE_RAKUTEN}" == "1" && "${GMC_I_AM_HUMAN}" != "1" ]]; then
  cat >&2 <<'EOF'
ERROR: --live-rakuten requires --i-am-human.
AI Agent must not run live. Human only.
Use --dry-run to inspect plan/queue/gates.
EOF
  exit 2
fi

if ! [[ "${GMC_MAX_RUNS_THIS_INVOCATION}" =~ ^[1-9][0-9]*$ ]]; then
  gmc_die "--max-runs-this-invocation must be a positive integer"
fi

gmc_mkdirs
gmc_load_dotenv_if_present

if [[ "${GMC_RESET_STATE}" == "1" ]]; then
  gmc_default_state_json >"${GMC_STATE_FILE}"
  gmc_log INFO "state reset to root queue [${GMC_ROOT_ID}]"
fi

gmc_ensure_state

if [[ -n "${GMC_SEED_QUEUE}" ]]; then
  GMC_STATE_FILE="${GMC_STATE_FILE}" GMC_SEED="${GMC_SEED_QUEUE}" gmc_python <<'PY'
import json, os
from datetime import datetime, timezone
path = os.environ["GMC_STATE_FILE"]
seed = [x.strip() for x in os.environ["GMC_SEED"].split(",") if x.strip()]
with open(path, encoding="utf-8") as f:
    data = json.load(f)
data["queue"] = seed
data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(",".join(seed))
PY
  gmc_log INFO "seed queue applied"
fi

echo "=== Genre map campaign runner ==="
echo "mode: $([[ "${GMC_DRY_RUN}" == "1" ]] && echo dry-run || echo live-human)"
echo "max_genre_ids_per_run: ${GMC_MAX_GENRE_IDS_PER_RUN}"
echo "campaign_max_qps: ${GMC_CAMPAIGN_MAX_QPS}"
echo "max_runs_this_invocation: ${GMC_MAX_RUNS_THIS_INVOCATION}"
echo "state: ${GMC_STATE_FILE}"
echo "parent shells: NOT used (leaf BATCH-001 only)"
echo "AI live: forbidden (this invocation live=$([[ ${GMC_LIVE_RAKUTEN} == 1 ]] && echo human-only || echo no))"
echo

queue_preview="$(gmc_state_get queue)"
echo "=== Queue (JSON) ==="
echo "${queue_preview}"
echo
gmc_print_gates
echo

if gmc_any_hard; then
  gmc_log ERROR "HARD gate reached — auto-stop (Decision §2.3)"
  gmc_slack_notify "error" "genre-map-campaign HARD stop" \
    "Hard capacity gate reached. Additional campaign runs forbidden until Human review." \
    "${GMC_DRY_RUN}"
  gmc_state_update "data['hard_stopped']=True"
  exit 3
fi

soft_list="$(gmc_soft_knobs || true)"
if [[ -n "${soft_list}" ]]; then
  gmc_log WARN "SOFT gate(s): ${soft_list//$'\n'/ }"
  gmc_slack_notify "warning" "genre-map-campaign SOFT threshold" \
    "Soft capacity threshold reached (${soft_list//$'\n'/, }). Run may continue; Human awareness." \
    "${GMC_DRY_RUN}"
fi

run_i=0
while [[ "${run_i}" -lt "${GMC_MAX_RUNS_THIS_INVOCATION}" ]]; do
  peek="$(gmc_peek_chunk "${GMC_MAX_GENRE_IDS_PER_RUN}")"
  if [[ -z "${peek}" ]]; then
    gmc_log INFO "queue empty — campaign complete (full tree) or nothing to do"
    break
  fi

  # Enforce ≤20 (peek already capped; double-check count)
  id_count="$(awk -F',' '{print NF}' <<<"${peek}")"
  if [[ "${id_count}" -gt "${GMC_MAX_GENRE_IDS_PER_RUN}" ]]; then
    gmc_die "internal error: chunk size ${id_count} > ${GMC_MAX_GENRE_IDS_PER_RUN}"
  fi

  job_run_id="$(gmc_generate_uuid)"
  echo "=== Planned Run $((run_i + 1)) ==="
  echo "genre-ids (${id_count} ≤ ${GMC_MAX_GENRE_IDS_PER_RUN}): ${peek}"
  echo "job-run-id: ${job_run_id}"
  echo "leaf command (dry-run path never includes --live-rakuten unless Human live):"
  if [[ "${GMC_DRY_RUN}" == "1" ]]; then
    gmc_build_leaf_cmd "${peek}" 0 "${job_run_id}"
    echo "(dry-run: command NOT executed; live would add --live-rakuten + --i-am-human on the runner)"
  else
    gmc_build_leaf_cmd "${peek}" 1 "${job_run_id}"
  fi
  echo

  if [[ "${GMC_DRY_RUN}" == "1" ]]; then
    # dry-run: do not mutate queue by taking chunk (peek only). Show remaining estimate.
    remaining="$(gmc_state_get queue | gmc_python -c "import json,sys; q=json.load(sys.stdin); print(max(0,len(q)-${id_count}))")"
    echo "dry-run remaining queue after this chunk (estimate): ${remaining}"
    echo "dry-run note: depth unlimited; stop on queue empty or HARD gate / Human interrupt / 429 / paused"
    run_i=$((run_i + 1))
    # In dry-run with max-runs>1, still only show the same first chunk unless --reset and multi-plan
    # For multi-run dry-run preview, temporarily take chunks without live.
    if [[ "${GMC_MAX_RUNS_THIS_INVOCATION}" -gt 1 ]]; then
      _chunk="$(gmc_take_chunk "${GMC_MAX_GENRE_IDS_PER_RUN}")"
      gmc_mark_expanded "${_chunk}"
      if [[ "${GMC_SKIP_DB_DISCOVER}" != "1" ]]; then
        gmc_discover_children_from_db
      fi
      gmc_print_gates
      echo
      if gmc_any_hard; then
        gmc_log ERROR "HARD gate during dry-run preview — stop"
        gmc_slack_notify "error" "genre-map-campaign HARD stop (dry-run preview)" \
          "Hard gate hit during dry-run multi-run preview." 1
        break
      fi
    else
      break
    fi
    continue
  fi

  # ---- Human live path ----
  # キュー消費は葉成功後のみ（失敗時に genre-ids が消失しないよう peek で実行し、成功後に take）。
  chunk="${peek}"
  export RAKUTEN_MAX_QPS="${GMC_CAMPAIGN_MAX_QPS}"
  gmc_log INFO "starting leaf BATCH-001 live (qps=${GMC_CAMPAIGN_MAX_QPS}) genre-ids=${chunk}"

  # set -e 下でも葉の非0を捕捉し、Slack / 明示停止へ到達させる。
  leaf_rc=0
  (
    cd "${GMC_REPO_ROOT}/apps/batch"
    # shellcheck disable=SC2086
    uv run python -m batch.application.genre_sync \
      --job-run-id "${job_run_id}" \
      --genre-ids "${chunk}" \
      --live-rakuten
  ) || leaf_rc=$?
  if [[ "${leaf_rc}" -ne 0 ]]; then
    gmc_log ERROR "leaf BATCH-001 failed rc=${leaf_rc} — stopping campaign loop (queue unchanged; chunk not consumed)"
    gmc_slack_notify "error" "genre-map-campaign leaf failure" \
      "BATCH-001 leaf failed (rc=${leaf_rc}). Campaign loop stopped. Queue preserved for resume. Check 429/paused." 0
    exit "${leaf_rc}"
  fi

  # 成功時のみキューからチャンクを確定消費し、expanded / discover へ進む。
  consumed="$(gmc_take_chunk "${GMC_MAX_GENRE_IDS_PER_RUN}")"
  if [[ "${consumed}" != "${chunk}" ]]; then
    gmc_die "internal error: post-success take_chunk mismatch (expected=${chunk} got=${consumed})"
  fi
  gmc_mark_expanded "${chunk}"
  if [[ "${GMC_SKIP_DB_DISCOVER}" != "1" ]]; then
    gmc_discover_children_from_db
  fi

  if gmc_any_hard; then
    gmc_log ERROR "HARD gate after run — auto-stop"
    gmc_slack_notify "error" "genre-map-campaign HARD stop" \
      "Hard capacity gate after live run. Further runs forbidden." 0
    gmc_state_update "data['hard_stopped']=True"
    exit 3
  fi

  soft_list="$(gmc_soft_knobs || true)"
  if [[ -n "${soft_list}" ]]; then
    gmc_slack_notify "warning" "genre-map-campaign SOFT threshold" \
      "Soft threshold after live run (${soft_list//$'\n'/, })." 0
  fi

  run_i=$((run_i + 1))
done

echo
echo "=== Done ==="
echo "mode=$([[ "${GMC_DRY_RUN}" == "1" ]] && echo dry-run || echo live-human) runs_this_invocation=${run_i}"
gmc_print_gates
echo "queue now: $(gmc_state_get queue)"
echo "Reminder: AI must not use --live-rakuten. MVP 4 genre IDs are not replaced by this campaign."
exit 0
