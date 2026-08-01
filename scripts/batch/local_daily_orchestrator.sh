#!/usr/bin/env bash
# local-daily: GHA batch-daily-orchestrator の Phase1 切り出し
# 順序: BATCH-002 → import連鎖(003→005→006→007→008→017任意)
# 意味生成(009〜) / distribution_metrics / retry は走らない。
# 実 crontab 登録は Human。secret 実値を出力しない。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/local_orchestrator_common.sh
source "${SCRIPT_DIR}/lib/local_orchestrator_common.sh"

usage() {
  cat <<'EOF'
Usage: local_daily_orchestrator.sh --dry-run | --live-rakuten [options]

Options:
  --dry-run                         順序・flock・Run IDのみ確認（外部副作用なし）
  --live-rakuten                    楽天HTTP live明示（egress照合は各Batch側）
  --pipeline-batch-run-id <uuid>    既存 pipeline ID を継続（省略時は新規）
  --from-step <name>                再開開始段（例: ranking_snapshot / item_pseudo_diff）
  --skip-import-summary             BATCH-017 をスキップ
  --no-import-chain                 003/004 の後の 005〜008 をスキップ
  --max-items <n>                   005〜008 件数上限（既定: MAX_ITEMS or 100）
  --pages-per-run <n>               BATCH-003（既定: 10 = 段階1）
  --cursors-per-run <n>             BATCH-003（既定: 1）
  --genre-ids <ids>                 BATCH-003 向け（既定: 100005。段階3で拡大する側）
  --ranking-genre-ids <ids>         BATCH-002 Ranking 向け（既定: 100005。#1765）
  --no-update-sort                  BATCH-003 で update_sort 除外（既定オン）
  --allow-update-sort               update_sort を許可
  --max-qps <n>                     BATCH-003 安全側 QPS 上書き

Step names: ranking_snapshot, item_pseudo_diff, raw_staging, product_diff,
            item_apply, item_active_status, import_summary

EOF
}

main() {
  if ! lor_parse_common_args "$@"; then
    usage
    exit 0
  fi

  lor_mkdirs
  LOR_LOG_FILE="${OUTPUT_DIR}/local-daily-$(date +%Y%m%dT%H%M%S).log"
  if [[ "${LOR_LIVE_RAKUTEN}" -eq 1 ]]; then
    lor_load_dotenv_if_present
  fi

  lor_begin_scenario "local-daily"
  local rc=0
  {
    local live_flags=()
    if [[ "${LOR_LIVE_RAKUTEN}" -eq 1 ]]; then
      # BATCH-002 の Raw 保存も live OS を使う（#1765 パターンBと同旨）
      live_flags+=(--live-rakuten --live-object-storage)
    fi
    local ranking_genre_flags=()
    if [[ -n "${LOR_RANKING_GENRE_IDS}" ]]; then
      ranking_genre_flags+=(--genre-ids "${LOR_RANKING_GENRE_IDS}")
    fi
    lor_run_batch_module_job_only "ranking_snapshot" "batch.application.ranking_snapshot" \
      "${live_flags[@]}" \
      "${ranking_genre_flags[@]}" \
      || rc=$?
    if [[ "${rc}" -eq 0 ]]; then
      lor_run_import_chain || rc=$?
    fi
  } || rc=$?

  lor_end_scenario "local-daily" "${rc}"
  exit "${rc}"
}

main "$@"
