#!/usr/bin/env bash
# local DB 読み取り専用データ可視化（127.0.0.1 のみ）。
# DATABASE_URL 実値は出力しない。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_python-lib.sh
source "${SCRIPT_DIR}/_python-lib.sh"

ROOT="$(python_lib_root)"
PORT="${LOCAL_DATA_BROWSER_PORT:-8787}"
HOST="127.0.0.1"

usage() {
  cat <<'EOF'
Usage: ./scripts/dev/start-local-data-browser.sh [--help]

Starts a localhost-only, read-only data browser for local PostgreSQL.
Listen: http://127.0.0.1:8787  (override port with LOCAL_DATA_BROWSER_PORT)
Ranking analysis: http://127.0.0.1:8787/ranking

Safety:
  - bind 127.0.0.1 only (not 0.0.0.0)
  - DATABASE_URL host must be 127.0.0.1 / localhost / ::1
  - APP_ENV must not be prod/stg
  - DB is SELECT only (ranking fetch writes local cache only)
  - not part of apps/web (will not be deployed to Vercel)

Prerequisites:
  - local Supabase / PostgreSQL
  - .env with DATABASE_URL (worktree or primary checkout)
  - uv (for apps/batch .venv / psycopg)
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

find_env_file() {
  if [[ -f "${ROOT}/.env" ]]; then
    printf '%s\n' "${ROOT}/.env"
    return 0
  fi
  local common main_root
  common="$(git -C "${ROOT}" rev-parse --git-common-dir 2>/dev/null || true)"
  if [[ -n "${common}" ]]; then
    main_root="$(cd "$(dirname "${common}")" && pwd)"
    if [[ -f "${main_root}/.env" ]]; then
      printf '%s\n' "${main_root}/.env"
      return 0
    fi
  fi
  return 1
}

ENV_FILE=""
if ENV_FILE="$(find_env_file)"; then
  set -a
  # shellcheck source=/dev/null
  source "${ENV_FILE}"
  set +a
  echo "info: loaded .env (path/values not printed)"
else
  echo "warn: .env not found; using current environment" >&2
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "error: DATABASE_URL is not set" >&2
  exit 2
fi

python_lib_require_uv
if ! python_lib_project_ready "${ROOT}/apps/batch"; then
  echo "error: apps/batch/pyproject.toml is not ready; cannot install psycopg" >&2
  exit 1
fi
if [[ ! -x "${ROOT}/apps/batch/.venv/bin/python" ]]; then
  echo "info: creating apps/batch/.venv"
  bash "${SCRIPT_DIR}/setup-python-batch.sh"
fi

PYTHON="${ROOT}/apps/batch/.venv/bin/python"
export PYTHONUNBUFFERED=1
exec "${PYTHON}" "${ROOT}/scripts/dev/local_data_browser/server.py" --host "${HOST}" --port "${PORT}" --root "${ROOT}"
