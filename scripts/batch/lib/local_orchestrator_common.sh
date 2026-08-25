#!/usr/bin/env bash
# local薄いオーケストレータ共通関数
# 正本: docs/15_運用・改善/運用手順/local薄いオーケストレータ設計・運用手順.md
# secret / .env 実値を echo しないこと。

set -euo pipefail

lor_repo_root() {
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
  printf '%s\n' "${here}"
}

REPO_ROOT="$(lor_repo_root)"
SCRIPTS_BATCH_DIR="${REPO_ROOT}/scripts/batch"
# locks は output-local-orchestrator 配下（scripts/batch/output-*/ が gitignore 済み）
OUTPUT_DIR="${SCRIPTS_BATCH_DIR}/output-local-orchestrator"
LOCK_DIR="${OUTPUT_DIR}/locks"
MAINLINE_LOCK="${LOCK_DIR}/local-batch-mainline.lock"
RAKUTEN_LIVE_LOCK="${LOCK_DIR}/local-rakuten-live.lock"

lor_mkdirs() {
  mkdir -p "${LOCK_DIR}" "${OUTPUT_DIR}"
}

lor_log() {
  # usage: lor_log LEVEL message...
  local level="$1"
  shift
  local ts
  ts="$(date -Iseconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z')"
  printf '%s [%s] %s\n' "${ts}" "${level}" "$*" | tee -a "${LOR_LOG_FILE:-/dev/null}" >&2
}

lor_die() {
  lor_log ERROR "$@"
  exit 1
}

lor_generate_uuid() {
  if command -v uuidgen >/dev/null 2>&1; then
    uuidgen | tr '[:upper:]' '[:lower:]'
    return 0
  fi
  python3 -c 'import uuid; print(uuid.uuid4())'
}

lor_load_dotenv_if_present() {
  # .env を読み込むが値は表示しない
  local env_file="${REPO_ROOT}/.env"
  if [[ -f "${env_file}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${env_file}"
    set +a
    lor_log INFO "loaded dotenv from repo root (values not logged)"
  else
    lor_log INFO "no .env at repo root (continuing with process env)"
  fi
}

lor_acquire_lock() {
  # usage: lor_acquire_lock LOCK_PATH FD_NUM DESCRIPTION
  local lock_path="$1"
  local fd_num="$2"
  local desc="$3"
  eval "exec ${fd_num}>\"${lock_path}\""
  if ! flock -n "${fd_num}"; then
    lor_die "failed to acquire ${desc} lock: ${lock_path} (another run holds it; will not cancel)"
  fi
  lor_log INFO "acquired ${desc} lock: ${lock_path}"
}

lor_release_lock() {
  local fd_num="$1"
  local desc="$2"
  flock -u "${fd_num}" || true
  eval "exec ${fd_num}>&-" || true
  lor_log INFO "released ${desc} lock"
}

lor_parse_common_args() {
  # Sets: LOR_DRY_RUN LOR_LIVE_RAKUTEN LOR_PIPELINE_ID LOR_FROM_STEP LOR_SKIP_017 LOR_MAX_ITEMS
  #        LOR_INCLUDE_IMPORT LOR_PAGES_PER_RUN LOR_CURSORS_PER_RUN
  #        LOR_GENRE_IDS（BATCH-003/001 取得・同期） LOR_RANKING_GENRE_IDS（BATCH-002）
  #        LOR_NO_UPDATE_SORT LOR_MAX_QPS
  #        LOR_RUN_MEANING（Phase2: 既定0=009〜016スキップ / --run-meaning で opt-in）
  #        LOR_SKIP_MEANING_SUMMARY LOR_MEANING_PIPELINE_ID LOR_SOURCE
  #        LOR_LIVE_EMBEDDING（BATCH-015 のみ。既定0 / --live-embedding で opt-in）
  LOR_DRY_RUN=0
  LOR_LIVE_RAKUTEN=0
  LOR_PIPELINE_ID=""
  LOR_FROM_STEP=""
  LOR_SKIP_017=0
  LOR_INCLUDE_IMPORT=1
  LOR_MAX_ITEMS="${MAX_ITEMS:-100}"
  # 段階1初期live相当（運用枠 Decision）
  LOR_PAGES_PER_RUN="${PAGES_PER_RUN:-10}"
  LOR_CURSORS_PER_RUN="${CURSORS_PER_RUN:-1}"
  # BATCH-003（および weekly の BATCH-001）向け。段階3でジャンル拡大する側。
  LOR_GENRE_IDS="${GENRE_IDS:-100005}"
  # BATCH-002 Ranking 専用（#1765: 100000/100003/100004 は Ranking HTTP 400）
  # --genre-ids を変えても Ranking 側は既定のまま残す（段階3拡大のため分離）
  LOR_RANKING_GENRE_IDS="${RANKING_GENRE_IDS:-100005}"
  LOR_NO_UPDATE_SORT=1
  LOR_MAX_QPS="${MAX_QPS:-}"
  # Phase2: 既定は Phase1 互換（009〜016 スキップ）。--run-meaning のみで有効化。
  LOR_RUN_MEANING=0
  LOR_SKIP_MEANING_EXPLICIT=0
  LOR_SKIP_MEANING_SUMMARY=0
  LOR_MEANING_PIPELINE_ID=""
  # 009 選定用: import / existing の BATCH-006 batch_run_id（#1880）
  LOR_DIFF_BATCH_RUN_ID=""
  LOR_SOURCE="${MEANING_SOURCE:-rakuten}"
  # BATCH-015: 既定は scaffold Embedding。--live-embedding で OpenAI live（課金）。
  # 環境変数 BATCH_EMBEDDING_LIVE=1 もモジュール側で有効（後方互換）。
  LOR_LIVE_EMBEDDING=0

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dry-run)
        LOR_DRY_RUN=1
        shift
        ;;
      --live-rakuten)
        LOR_LIVE_RAKUTEN=1
        shift
        ;;
      --pipeline-batch-run-id=*)
        LOR_PIPELINE_ID="${1#*=}"
        shift
        ;;
      --pipeline-batch-run-id)
        LOR_PIPELINE_ID="${2:-}"
        shift 2
        ;;
      --from-step=*)
        LOR_FROM_STEP="${1#*=}"
        shift
        ;;
      --from-step)
        LOR_FROM_STEP="${2:-}"
        shift 2
        ;;
      --skip-import-summary)
        LOR_SKIP_017=1
        shift
        ;;
      --no-import-chain)
        LOR_INCLUDE_IMPORT=0
        shift
        ;;
      --run-meaning)
        LOR_RUN_MEANING=1
        shift
        ;;
      --live-embedding)
        LOR_LIVE_EMBEDDING=1
        shift
        ;;
      --skip-meaning)
        LOR_SKIP_MEANING_EXPLICIT=1
        shift
        ;;
      --skip-meaning-summary)
        LOR_SKIP_MEANING_SUMMARY=1
        shift
        ;;
      --meaning-pipeline-batch-run-id=*)
        LOR_MEANING_PIPELINE_ID="${1#*=}"
        shift
        ;;
      --meaning-pipeline-batch-run-id)
        LOR_MEANING_PIPELINE_ID="${2:-}"
        shift 2
        ;;
      --source=*)
        LOR_SOURCE="${1#*=}"
        shift
        ;;
      --source)
        LOR_SOURCE="${2:-}"
        shift 2
        ;;
      --max-items=*)
        LOR_MAX_ITEMS="${1#*=}"
        shift
        ;;
      --max-items)
        LOR_MAX_ITEMS="${2:-}"
        shift 2
        ;;
      --pages-per-run=*)
        LOR_PAGES_PER_RUN="${1#*=}"
        shift
        ;;
      --pages-per-run)
        LOR_PAGES_PER_RUN="${2:-}"
        shift 2
        ;;
      --cursors-per-run=*)
        LOR_CURSORS_PER_RUN="${1#*=}"
        shift
        ;;
      --cursors-per-run)
        LOR_CURSORS_PER_RUN="${2:-}"
        shift 2
        ;;
      --genre-ids=*)
        LOR_GENRE_IDS="${1#*=}"
        shift
        ;;
      --genre-ids)
        LOR_GENRE_IDS="${2:-}"
        shift 2
        ;;
      --ranking-genre-ids=*)
        LOR_RANKING_GENRE_IDS="${1#*=}"
        shift
        ;;
      --ranking-genre-ids)
        LOR_RANKING_GENRE_IDS="${2:-}"
        shift 2
        ;;
      --no-update-sort)
        LOR_NO_UPDATE_SORT=1
        shift
        ;;
      --allow-update-sort)
        LOR_NO_UPDATE_SORT=0
        shift
        ;;
      --max-qps=*)
        LOR_MAX_QPS="${1#*=}"
        shift
        ;;
      --max-qps)
        LOR_MAX_QPS="${2:-}"
        shift 2
        ;;
      -h|--help)
        return 2
        ;;
      *)
        lor_die "unknown argument: $1"
        ;;
    esac
  done

  if [[ "${LOR_DRY_RUN}" -eq 0 && "${LOR_LIVE_RAKUTEN}" -eq 0 ]]; then
    lor_die "either --dry-run or --live-rakuten is required (refuse implicit live)"
  fi
  if [[ "${LOR_DRY_RUN}" -eq 1 && "${LOR_LIVE_RAKUTEN}" -eq 1 ]]; then
    lor_die "--dry-run and --live-rakuten are mutually exclusive"
  fi
  if [[ "${LOR_RUN_MEANING}" -eq 1 && "${LOR_SKIP_MEANING_EXPLICIT}" -eq 1 ]]; then
    lor_die "--run-meaning and --skip-meaning are mutually exclusive"
  fi
  # --skip-meaning は既定 skip と同義（明示ログ用）。両方無い＝skip。
  if [[ "${LOR_SKIP_MEANING_EXPLICIT}" -eq 1 ]]; then
    LOR_RUN_MEANING=0
  fi
  if [[ -z "${LOR_PIPELINE_ID}" ]]; then
    LOR_PIPELINE_ID="$(lor_generate_uuid)"
  fi
  # 009 選定の既定対象はシナリオ（import）pipeline。weekly existing 成功後に上書きする。
  if [[ -z "${LOR_DIFF_BATCH_RUN_ID}" ]]; then
    LOR_DIFF_BATCH_RUN_ID="${LOR_PIPELINE_ID}"
  fi
}

lor_step_reached() {
  # return 0 if current step should run given LOR_FROM_STEP
  local step="$1"
  if [[ -z "${LOR_FROM_STEP}" ]]; then
    return 0
  fi
  if [[ "${LOR_SKIPPING}" -eq 0 ]]; then
    return 0
  fi
  if [[ "${step}" == "${LOR_FROM_STEP}" ]]; then
    LOR_SKIPPING=0
    return 0
  fi
  return 1
}

lor_run_batch_module() {
  # usage: lor_run_batch_module STEP_NAME MODULE -- args...
  local step_name="$1"
  local module="$2"
  shift 2

  if ! lor_step_reached "${step_name}"; then
    lor_log INFO "skip step (before --from-step): ${step_name}"
    return 0
  fi

  local job_run_id
  job_run_id="$(lor_generate_uuid)"
  lor_log INFO "STEP start name=${step_name} module=${module} pipeline_batch_run_id=${LOR_PIPELINE_ID} job_run_id=${job_run_id}"

  if [[ "${LOR_DRY_RUN}" -eq 1 ]]; then
    lor_log INFO "DRY-RUN would run: uv run python -m ${module} --job-run-id ${job_run_id} --batch-run-id ${LOR_PIPELINE_ID} $*"
    lor_log INFO "STEP ok (dry-run) name=${step_name}"
    return 0
  fi

  (
    cd "${REPO_ROOT}/apps/batch"
    # shellcheck disable=SC2068
    uv run python -m "${module}" \
      --job-run-id "${job_run_id}" \
      --batch-run-id "${LOR_PIPELINE_ID}" \
      "$@"
  )
  local rc=$?
  if [[ "${rc}" -ne 0 ]]; then
    lor_log ERROR "STEP failed name=${step_name} exit=${rc} pipeline_batch_run_id=${LOR_PIPELINE_ID}"
    return "${rc}"
  fi
  lor_log INFO "STEP ok name=${step_name}"
  return 0
}

# Modules that use --job-run-id as primary run id（--batch-run-id を持たない葉）
# 葉ごとに UUID を発行する。pipeline_batch_run_id は業務紐付け用に別引数（--diff-batch-run-id 等）で渡す。
# （同一 pipeline ID を複数葉の batch_run_log PK に使うと UniqueViolation になる）
lor_run_batch_module_job_only() {
  local step_name="$1"
  local module="$2"
  shift 2

  if ! lor_step_reached "${step_name}"; then
    lor_log INFO "skip step (before --from-step): ${step_name}"
    return 0
  fi

  local job_run_id
  job_run_id="$(lor_generate_uuid)"
  lor_log INFO "STEP start name=${step_name} module=${module} pipeline_batch_run_id=${LOR_PIPELINE_ID} job_run_id=${job_run_id}"

  if [[ "${LOR_DRY_RUN}" -eq 1 ]]; then
    lor_log INFO "DRY-RUN would run: uv run python -m ${module} --job-run-id ${job_run_id} $*"
    lor_log INFO "STEP ok (dry-run) name=${step_name}"
    return 0
  fi

  (
    cd "${REPO_ROOT}/apps/batch"
    # shellcheck disable=SC2068
    uv run python -m "${module}" \
      --job-run-id "${job_run_id}" \
      "$@"
  )
  local rc=$?
  if [[ "${rc}" -ne 0 ]]; then
    lor_log ERROR "STEP failed name=${step_name} exit=${rc} pipeline_batch_run_id=${LOR_PIPELINE_ID}"
    return "${rc}"
  fi
  lor_log INFO "STEP ok name=${step_name}"
  return 0
}

lor_run_import_chain() {
  # 003→005→006→007→008→(017)
  local live_flags=()
  if [[ "${LOR_LIVE_RAKUTEN}" -eq 1 ]]; then
    live_flags+=(--live-rakuten --live-object-storage)
  fi
  local genre_flags=()
  if [[ -n "${LOR_GENRE_IDS}" ]]; then
    genre_flags+=(--genre-ids "${LOR_GENRE_IDS}")
  fi
  local batch003_extra=()
  if [[ "${LOR_NO_UPDATE_SORT}" -eq 1 ]]; then
    batch003_extra+=(--no-update-sort)
  fi
  if [[ -n "${LOR_MAX_QPS}" ]]; then
    batch003_extra+=(--max-qps "${LOR_MAX_QPS}")
  fi

  lor_run_batch_module "item_pseudo_diff" "batch.application.item_pseudo_diff" \
    "${live_flags[@]}" \
    "${genre_flags[@]}" \
    --pages-per-run "${LOR_PAGES_PER_RUN}" \
    --cursors-per-run "${LOR_CURSORS_PER_RUN}" \
    "${batch003_extra[@]}" \
    || return $?

  if [[ "${LOR_INCLUDE_IMPORT}" -eq 0 ]]; then
    lor_log INFO "import chain after 003 skipped (--no-import-chain)"
    return 0
  fi

  local storage_flags=()
  if [[ "${LOR_LIVE_RAKUTEN}" -eq 1 ]]; then
    storage_flags+=(--live-object-storage)
  fi

  lor_run_batch_module "raw_staging" "batch.application.raw_staging" \
    "${storage_flags[@]}" \
    || return $?

  lor_run_batch_module "product_diff" "batch.application.product_diff" \
    || return $?

  lor_run_batch_module_job_only "item_apply" "batch.application.item_apply" \
    --max-items "${LOR_MAX_ITEMS}" \
    --diff-batch-run-id "${LOR_PIPELINE_ID}" \
    || return $?

  lor_run_batch_module_job_only "item_active_status" "batch.application.item_active_status" \
    --max-items "${LOR_MAX_ITEMS}" \
    --batch-run-id "${LOR_PIPELINE_ID}" \
    || return $?

  if [[ "${LOR_SKIP_017}" -eq 0 ]]; then
    lor_run_batch_module "import_summary" "batch.application.import_summary" \
      || return $?
  else
    lor_log INFO "skip BATCH-017 import_summary (--skip-import-summary)"
  fi
}

lor_run_existing_item_chain() {
  # 004→005→006→007→008→(017)
  # GHA batch-rakuten-existing-item-pipeline の resolve-run-id 相当を別発行する。
  # BATCH-004 は object_key に job_run_id を埋める（--batch-run-id なし）。
  # 葉ごとに別 UUID を渡すと 005 がシナリオ pipeline ID で Raw を探せなくなり
  # empty staging_plan (GRS-BAT-001) になるため、004〜017 は同一 business ID を使う。
  # シナリオ全体の LOR_PIPELINE_ID（003 import 用）とは分離する。
  local scenario_pipeline_id="${LOR_PIPELINE_ID}"
  local existing_pipeline_id
  existing_pipeline_id="$(lor_generate_uuid)"
  lor_log INFO "existing_item_chain business_run_id=${existing_pipeline_id} scenario_pipeline_id=${scenario_pipeline_id}"

  local live_flags=()
  if [[ "${LOR_LIVE_RAKUTEN}" -eq 1 ]]; then
    live_flags+=(--live-rakuten --live-object-storage)
  fi

  if lor_step_reached "item_recheck"; then
    lor_log INFO "STEP start name=item_recheck module=batch.application.item_recheck pipeline_batch_run_id=${existing_pipeline_id} job_run_id=${existing_pipeline_id}"
    if [[ "${LOR_DRY_RUN}" -eq 1 ]]; then
      lor_log INFO "DRY-RUN would run: uv run python -m batch.application.item_recheck --job-run-id ${existing_pipeline_id} ${live_flags[*]:-} --max-items ${LOR_MAX_ITEMS}"
      lor_log INFO "STEP ok (dry-run) name=item_recheck"
    else
      (
        cd "${REPO_ROOT}/apps/batch"
        # shellcheck disable=SC2068
        uv run python -m batch.application.item_recheck \
          --job-run-id "${existing_pipeline_id}" \
          ${live_flags[@]+"${live_flags[@]}"} \
          --max-items "${LOR_MAX_ITEMS}"
      )
      local recheck_rc=$?
      if [[ "${recheck_rc}" -ne 0 ]]; then
        lor_log ERROR "STEP failed name=item_recheck exit=${recheck_rc} pipeline_batch_run_id=${existing_pipeline_id}"
        return "${recheck_rc}"
      fi
      lor_log INFO "STEP ok name=item_recheck"
    fi
  else
    lor_log INFO "skip step (before --from-step): item_recheck"
  fi

  if [[ "${LOR_INCLUDE_IMPORT}" -eq 0 ]]; then
    lor_log INFO "import chain after 004 skipped (--no-import-chain)"
    return 0
  fi

  # 005〜017 の --batch-run-id / --diff-batch-run-id を existing business ID に合わせる
  LOR_PIPELINE_ID="${existing_pipeline_id}"
  local chain_rc=0
  local storage_flags=()
  if [[ "${LOR_LIVE_RAKUTEN}" -eq 1 ]]; then
    storage_flags+=(--live-object-storage)
  fi

  lor_run_batch_module "raw_staging" "batch.application.raw_staging" \
    "${storage_flags[@]}" \
    || chain_rc=$?

  if [[ "${chain_rc}" -eq 0 ]]; then
    lor_run_batch_module "product_diff" "batch.application.product_diff" \
      || chain_rc=$?
  fi

  if [[ "${chain_rc}" -eq 0 ]]; then
    lor_run_batch_module_job_only "item_apply" "batch.application.item_apply" \
      --max-items "${LOR_MAX_ITEMS}" \
      --diff-batch-run-id "${LOR_PIPELINE_ID}" \
      || chain_rc=$?
  fi

  if [[ "${chain_rc}" -eq 0 ]]; then
    lor_run_batch_module_job_only "item_active_status" "batch.application.item_active_status" \
      --max-items "${LOR_MAX_ITEMS}" \
      --batch-run-id "${LOR_PIPELINE_ID}" \
      || chain_rc=$?
  fi

  if [[ "${chain_rc}" -eq 0 ]]; then
    if [[ "${LOR_SKIP_017}" -eq 0 ]]; then
      lor_run_batch_module "import_summary" "batch.application.import_summary" \
        || chain_rc=$?
    else
      lor_log INFO "skip BATCH-017 import_summary (--skip-import-summary)"
    fi
  fi

  LOR_PIPELINE_ID="${scenario_pipeline_id}"
  # meaning 009 は直近 BATCH-006（existing）を優先し、残枠でバックログ消化（#1880 C）
  LOR_DIFF_BATCH_RUN_ID="${existing_pipeline_id}"
  return "${chain_rc}"
}

lor_run_meaning_chain() {
  # GHA batch-item-meaning-generation 相当: 009→010→011→012→013→014→015→(017 meaning)
  # Phase1 互換: 既定スキップ。--run-meaning でのみ実行（設計 §14）。
  # 意味連鎖の pipeline_batch_run_id は import / existing と混在させない（設計 §13.3）。
  if [[ "${LOR_RUN_MEANING}" -eq 0 ]]; then
    lor_log INFO "skip meaning chain (Phase1 compat; pass --run-meaning to enable BATCH-009〜016)"
    return 0
  fi

  local scenario_pipeline_id="${LOR_PIPELINE_ID}"
  local meaning_pipeline_id
  if [[ -n "${LOR_MEANING_PIPELINE_ID}" ]]; then
    meaning_pipeline_id="${LOR_MEANING_PIPELINE_ID}"
  else
    meaning_pipeline_id="$(lor_generate_uuid)"
  fi
  lor_log INFO "meaning_chain pipeline_batch_run_id=${meaning_pipeline_id} scenario_pipeline_id=${scenario_pipeline_id} diff_batch_run_id=${LOR_DIFF_BATCH_RUN_ID:-${scenario_pipeline_id}}"

  LOR_PIPELINE_ID="${meaning_pipeline_id}"
  local chain_rc=0
  local meaning_flags=(--max-items "${LOR_MAX_ITEMS}" --source "${LOR_SOURCE}")
  local queue_flags=(
    "${meaning_flags[@]}"
    --diff-batch-run-id "${LOR_DIFF_BATCH_RUN_ID:-${scenario_pipeline_id}}"
    --include-backlog
  )

  lor_run_batch_module_job_only "item_generation_queue" "batch.application.item_generation_queue" \
    "${queue_flags[@]}" \
    || chain_rc=$?

  if [[ "${chain_rc}" -eq 0 ]]; then
    lor_run_batch_module_job_only "item_semantic" "batch.application.item_semantic" \
      "${meaning_flags[@]}" \
      || chain_rc=$?
  fi

  if [[ "${chain_rc}" -eq 0 ]]; then
    lor_run_batch_module_job_only "feature_input_hash" "batch.application.feature_input_hash" \
      "${meaning_flags[@]}" \
      || chain_rc=$?
  fi

  if [[ "${chain_rc}" -eq 0 ]]; then
    lor_run_batch_module_job_only "item_feature" "batch.application.item_feature" \
      "${meaning_flags[@]}" \
      || chain_rc=$?
  fi

  if [[ "${chain_rc}" -eq 0 ]]; then
    lor_run_batch_module_job_only "feature_normalization" "batch.application.feature_normalization" \
      "${meaning_flags[@]}" \
      || chain_rc=$?
  fi

  if [[ "${chain_rc}" -eq 0 ]]; then
    lor_run_batch_module_job_only "embedding_input_hash" "batch.application.embedding_input_hash" \
      "${meaning_flags[@]}" \
      || chain_rc=$?
  fi

  if [[ "${chain_rc}" -eq 0 ]]; then
    local embedding_flags=("${meaning_flags[@]}")
    if [[ "${LOR_LIVE_EMBEDDING}" -eq 1 ]]; then
      embedding_flags+=(--live-embedding)
    fi
    lor_run_batch_module_job_only "item_embedding" "batch.application.item_embedding" \
      "${embedding_flags[@]}" \
      || chain_rc=$?
  fi

  if [[ "${chain_rc}" -eq 0 ]]; then
    if [[ "${LOR_SKIP_MEANING_SUMMARY}" -eq 0 ]]; then
      # 017: 葉 job_run_id は新規、集計対象は meaning pipeline（--batch-run-id）
      lor_run_batch_module "meaning_summary" "batch.application.import_summary" \
        || chain_rc=$?
    else
      lor_log INFO "skip meaning BATCH-017 import_summary (--skip-meaning-summary)"
    fi
  fi

  LOR_PIPELINE_ID="${scenario_pipeline_id}"
  return "${chain_rc}"
}

lor_run_distribution_metrics() {
  # GHA batch-distribution-metrics / trigger_mode=chain 相当（BATCH-016）
  # Phase1 互換では 009〜016 ごとスキップ（--run-meaning 必須）。
  if [[ "${LOR_RUN_MEANING}" -eq 0 ]]; then
    lor_log INFO "skip distribution_metrics (Phase1 compat; requires --run-meaning)"
    return 0
  fi

  lor_run_batch_module_job_only "distribution_metrics" "batch.application.distribution_metrics" \
    --trigger-mode chain \
    || return $?
}

lor_begin_scenario() {
  local scenario="$1"
  lor_mkdirs
  if [[ -z "${LOR_LOG_FILE:-}" ]]; then
    LOR_LOG_FILE="${OUTPUT_DIR}/${scenario}-$(date +%Y%m%dT%H%M%S).log"
  fi
  lor_log INFO "scenario=${scenario} pipeline_batch_run_id=${LOR_PIPELINE_ID} dry_run=${LOR_DRY_RUN} live_rakuten=${LOR_LIVE_RAKUTEN} run_meaning=${LOR_RUN_MEANING} live_embedding=${LOR_LIVE_EMBEDDING}"
  lor_log INFO "max_items=${LOR_MAX_ITEMS} pages_per_run=${LOR_PAGES_PER_RUN} cursors_per_run=${LOR_CURSORS_PER_RUN} genre_ids=${LOR_GENRE_IDS:-"(unset)"} ranking_genre_ids=${LOR_RANKING_GENRE_IDS:-"(unset)"} no_update_sort=${LOR_NO_UPDATE_SORT} max_qps=${LOR_MAX_QPS:-"(batch-default)"} source=${LOR_SOURCE} from_step=${LOR_FROM_STEP:-"(start)"}"
  if [[ -n "${LOR_FROM_STEP}" ]]; then
    LOR_SKIPPING=1
  else
    LOR_SKIPPING=0
  fi
  lor_acquire_lock "${MAINLINE_LOCK}" 9 "mainline"
  if [[ "${LOR_LIVE_RAKUTEN}" -eq 1 ]]; then
    lor_acquire_lock "${RAKUTEN_LIVE_LOCK}" 8 "rakuten-live"
  fi
}

lor_end_scenario() {
  local scenario="$1"
  local rc="$2"
  if [[ "${LOR_LIVE_RAKUTEN}" -eq 1 ]]; then
    lor_release_lock 8 "rakuten-live"
  fi
  lor_release_lock 9 "mainline"
  if [[ "${rc}" -eq 0 ]]; then
    lor_log INFO "scenario=${scenario} SUCCEEDED pipeline_batch_run_id=${LOR_PIPELINE_ID}"
  else
    lor_log ERROR "scenario=${scenario} FAILED exit=${rc} pipeline_batch_run_id=${LOR_PIPELINE_ID} (subsequent steps were not started after failure)"
  fi
  return "${rc}"
}
