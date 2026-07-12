#!/usr/bin/env bash
# Root uv workspace: create .venv (per worktree) and sync dev dependencies.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_python-lib.sh
source "${SCRIPT_DIR}/_python-lib.sh"

ROOT="$(python_lib_root)"
python_lib_require_uv
cd "${ROOT}"

PY="$(python_lib_python_version "${ROOT}")"

if [[ ! -f "${ROOT}/pyproject.toml" ]]; then
  echo "error: root pyproject.toml not found" >&2
  exit 1
fi

echo "info: Python ${PY} — uv workspace sync (root .venv per worktree)"
if [[ ! -d "${ROOT}/.venv" ]]; then
  uv venv --python "${PY}" "${ROOT}/.venv"
fi
UV_PROJECT_ENVIRONMENT="${ROOT}/.venv" uv sync --all-packages --group dev

echo "info: workspace ready. Run ./scripts/dev/pytest-python.sh"
