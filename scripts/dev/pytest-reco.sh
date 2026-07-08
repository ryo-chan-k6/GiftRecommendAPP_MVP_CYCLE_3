#!/usr/bin/env bash
# Run apps/reco unit tests when scaffold exists; skip otherwise.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_python-lib.sh
source "${SCRIPT_DIR}/_python-lib.sh"

ROOT="$(python_lib_root)"
RECO_DIR="${ROOT}/apps/reco"
python_lib_require_uv

usage() {
  cat <<'EOF'
Usage: ./scripts/dev/pytest-reco.sh [--help]

Runs apps/reco/tests/unit via uv when reco-foundation scaffold is present.
Skips with exit 0 when tests or pyproject.toml are not ready.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

if ! python_lib_reco_tests_ready "${ROOT}"; then
  echo "info: skip — apps/reco unit tests not present (awaiting reco-foundation merge)"
  exit 0
fi

if [[ ! -d "${RECO_DIR}/.venv" ]]; then
  echo "info: apps/reco/.venv not found — running setup-python-reco.sh"
  "${SCRIPT_DIR}/setup-python-reco.sh"
fi

export UV_PROJECT_ENVIRONMENT="${RECO_DIR}/.venv"
cd "${RECO_DIR}"

echo "info: pytest — apps/reco/tests/unit"
uv run pytest tests/unit -q

echo "info: reco unit tests passed"
