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
LOCK_DIR="${SCRIPTS_BATCH_DIR}/locks"
OUTPUT_DIR="${SCRIPTS_BATCH_DIR}/output-local-orchestrator"
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
      --cursors-per-run=*)
        LOR_CURSORS_PER_RUN="${1#*=}"
        shift
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
  if [[ -z "${LOR_PIPELINE_ID}" ]]; then
    LOR_PIPELINE_ID="$(lor_generate_uuid)"
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

# Modules that use --job-run-id as primary business id (no --batch-run-id)
lor_run_batch_module_job_only() {
  local step_name="$1"
  local module="$2"
  shift 2

  if ! lor_step_reached "${step_name}"; then
    lor_log INFO "skip step (before --from-step): ${step_name}"
    return 0
  fi

  local job_run_id="${LOR_PIPELINE_ID}"
  lor_log INFO "STEP start name=${step_name} module=${module} job_run_id=${job_run_id}"

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

  lor_run_batch_module "item_pseudo_diff" "batch.application.item_pseudo_diff" \
    "${live_flags[@]}" \
    --pages-per-run "${LOR_PAGES_PER_RUN}" \
    --cursors-per-run "${LOR_CURSORS_PER_RUN}" \
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
  local live_flags=()
  if [[ "${LOR_LIVE_RAKUTEN}" -eq 1 ]]; then
    live_flags+=(--live-rakuten --live-object-storage)
  fi

  lor_run_batch_module_job_only "item_recheck" "batch.application.item_recheck" \
    "${live_flags[@]}" \
    --max-items "${LOR_MAX_ITEMS}" \
    || return $?

  if [[ "${LOR_INCLUDE_IMPORT}" -eq 0 ]]; then
    lor_log INFO "import chain after 004 skipped (--no-import-chain)"
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

lor_begin_scenario() {
  local scenario="$1"
  lor_mkdirs
  if [[ -z "${LOR_LOG_FILE:-}" ]]; then
    LOR_LOG_FILE="${OUTPUT_DIR}/${scenario}-$(date +%Y%m%dT%H%M%S).log"
  fi
  lor_log INFO "scenario=${scenario} pipeline_batch_run_id=${LOR_PIPELINE_ID} dry_run=${LOR_DRY_RUN} live_rakuten=${LOR_LIVE_RAKUTEN}"
  lor_log INFO "max_items=${LOR_MAX_ITEMS} pages_per_run=${LOR_PAGES_PER_RUN} cursors_per_run=${LOR_CURSORS_PER_RUN} from_step=${LOR_FROM_STEP:-"(start)"}"
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
