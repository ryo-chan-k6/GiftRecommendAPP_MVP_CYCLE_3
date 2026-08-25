#!/usr/bin/env bash
# local-weekly: GHA batch-weekly-orchestrator の Phase1+Phase2 切り出し
# 順序: BATCH-001 → 002 → import連鎖(003…) → existing連鎖(004…)
#       →（--run-meaning 時）meaning連鎖 → BATCH-016（existing 成功後に1回のみ）
# 当日は local-daily を別途起動しない。既定は Phase1 互換（009〜016 スキップ）。
# 018 Offline Evaluation は載せない。実 crontab 登録は Human。secret 実値を出力しない。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/local_orchestrator_common.sh
source "${SCRIPT_DIR}/lib/local_orchestrator_common.sh"

usage() {
  cat <<'EOF'
Usage: local_weekly_orchestrator.sh --dry-run | --live-rakuten [options]

Options: same as local_daily_orchestrator.sh
  （--run-meaning / --skip-meaning / --skip-meaning-summary /
   --meaning-pipeline-batch-run-id / --source を含む）

Step names: genre_sync, ranking_snapshot, item_pseudo_diff, raw_staging, product_diff,
            item_apply, item_active_status, import_summary, item_recheck,
            item_generation_queue, item_semantic, feature_input_hash, item_feature,
            feature_normalization, embedding_input_hash, item_embedding,
            meaning_summary, distribution_metrics
            (import_summary / raw_staging 等は 003 連鎖と 004 連鎖で重複し得る。
             --from-step は最初に現れる段名から再開する)

EOF
}

main() {
  if ! lor_parse_common_args "$@"; then
    usage
    exit 0
  fi

  lor_mkdirs
  LOR_LOG_FILE="${OUTPUT_DIR}/local-weekly-$(date +%Y%m%dT%H%M%S).log"
  if [[ "${LOR_LIVE_RAKUTEN}" -eq 1 ]]; then
    lor_load_dotenv_if_present
  fi

  lor_begin_scenario "local-weekly"
  local rc=0
  {
    local live_flags=()
    if [[ "${LOR_LIVE_RAKUTEN}" -eq 1 ]]; then
      live_flags+=(--live-rakuten --live-object-storage)
    fi
    local fetch_genre_flags=()
    if [[ -n "${LOR_GENRE_IDS}" ]]; then
      fetch_genre_flags+=(--genre-ids "${LOR_GENRE_IDS}")
    fi
    local ranking_genre_flags=()
    if [[ -n "${LOR_RANKING_GENRE_IDS}" ]]; then
      ranking_genre_flags+=(--genre-ids "${LOR_RANKING_GENRE_IDS}")
    fi

    # BATCH-001: 拡大対象ジャンルを同期（段階3）
    lor_run_batch_module_job_only "genre_sync" "batch.application.genre_sync" \
      "${live_flags[@]}" \
      "${fetch_genre_flags[@]}" \
      || rc=$?
    if [[ "${rc}" -ne 0 ]]; then
      :
    else
      # BATCH-002: Ranking 対応ジャンルのみ（既定 100005）
      lor_run_batch_module_job_only "ranking_snapshot" "batch.application.ranking_snapshot" \
        "${live_flags[@]}" \
        "${ranking_genre_flags[@]}" \
        || rc=$?
    fi
    if [[ "${rc}" -eq 0 ]]; then
      lor_run_import_chain || rc=$?
    fi
    if [[ "${rc}" -eq 0 ]]; then
      lor_run_existing_item_chain || rc=$?
    fi
    # GHA weekly: existing_item_pipeline → item_meaning_generation（import 直後には載せない）
    if [[ "${rc}" -eq 0 ]]; then
      lor_run_meaning_chain || rc=$?
    fi
    if [[ "${rc}" -eq 0 ]]; then
      lor_run_distribution_metrics || rc=$?
    fi
  } || rc=$?

  lor_end_scenario "local-weekly" "${rc}"
  exit "${rc}"
}

main "$@"
