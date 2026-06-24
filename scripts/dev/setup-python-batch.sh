#!/usr/bin/env bash
# apps/batch: per-project .venv (per worktree) when pyproject.toml is ready.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_python-lib.sh
source "${SCRIPT_DIR}/_python-lib.sh"

ROOT="$(python_lib_root)"
BATCH_DIR="${ROOT}/apps/batch"
python_lib_require_uv

usage() {
  cat <<'EOF'
Usage: ./scripts/dev/setup-python-batch.sh [--help]

Creates apps/batch/.venv and installs editable dev dependencies when
apps/batch/pyproject.toml defines [project] (batch-foundation scaffold).

Skips with exit 0 when pyproject is not ready yet.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

if ! python_lib_project_ready "${BATCH_DIR}"; then
  echo "info: skip — apps/batch/pyproject.toml is not ready (awaiting batch-foundation merge)"
  exit 0
fi

PY="$(python_lib_python_version "${ROOT}")"
cd "${BATCH_DIR}"

echo "info: Python ${PY} — apps/batch/.venv (per worktree)"
if [[ ! -d "${BATCH_DIR}/.venv" ]]; then
  uv venv --python "${PY}" "${BATCH_DIR}/.venv"
fi
UV_PROJECT_ENVIRONMENT="${BATCH_DIR}/.venv" uv pip install -e ".[dev]"

echo "info: batch Python env ready. Run ./scripts/dev/pytest-batch.sh"
