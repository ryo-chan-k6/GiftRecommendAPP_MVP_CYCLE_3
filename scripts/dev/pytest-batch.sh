#!/usr/bin/env bash
# Run apps/batch unit tests when scaffold exists; skip otherwise.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_python-lib.sh
source "${SCRIPT_DIR}/_python-lib.sh"

ROOT="$(python_lib_root)"
BATCH_DIR="${ROOT}/apps/batch"
python_lib_require_uv

usage() {
  cat <<'EOF'
Usage: ./scripts/dev/pytest-batch.sh [--help]

Runs apps/batch/tests/unit via uv when batch-foundation scaffold is present.
Skips with exit 0 when tests or pyproject.toml are not ready.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

if ! python_lib_batch_tests_ready "${ROOT}"; then
  echo "info: skip — apps/batch unit tests not present (awaiting batch-foundation merge)"
  exit 0
fi

if [[ ! -d "${BATCH_DIR}/.venv" ]]; then
  echo "info: apps/batch/.venv not found — running setup-python-batch.sh"
  "${SCRIPT_DIR}/setup-python-batch.sh"
fi

export UV_PROJECT_ENVIRONMENT="${BATCH_DIR}/.venv"
cd "${BATCH_DIR}"

echo "info: pytest — apps/batch/tests/unit"
uv run pytest tests/unit -q

echo "info: batch unit tests passed"
