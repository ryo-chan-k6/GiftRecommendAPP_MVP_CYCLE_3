#!/usr/bin/env bash
# apps/reco: per-project .venv (per worktree) when pyproject.toml is ready.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_python-lib.sh
source "${SCRIPT_DIR}/_python-lib.sh"

ROOT="$(python_lib_root)"
RECO_DIR="${ROOT}/apps/reco"
python_lib_require_uv

usage() {
  cat <<'EOF'
Usage: ./scripts/dev/setup-python-reco.sh [--help]

Creates apps/reco/.venv and installs editable dev dependencies when
apps/reco/pyproject.toml defines [project] (reco-foundation scaffold).

Skips with exit 0 when pyproject is not ready yet.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

if ! python_lib_project_ready "${RECO_DIR}"; then
  echo "info: skip — apps/reco/pyproject.toml is not ready (awaiting reco-foundation merge)"
  exit 0
fi

PY="$(python_lib_python_version "${ROOT}")"
cd "${RECO_DIR}"

echo "info: Python ${PY} — apps/reco/.venv (per worktree)"
if [[ ! -d "${RECO_DIR}/.venv" ]]; then
  uv venv --python "${PY}" "${RECO_DIR}/.venv"
fi
UV_PROJECT_ENVIRONMENT="${RECO_DIR}/.venv" uv pip install -e ".[dev]"

echo "info: reco Python env ready. Run ./scripts/dev/pytest-reco.sh"
