#!/usr/bin/env bash
# Run Python unit tests for uv workspace packages (shared-logic, test-fixtures).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_python-lib.sh
source "${SCRIPT_DIR}/_python-lib.sh"

ROOT="$(python_lib_root)"
python_lib_require_uv
cd "${ROOT}"

if [[ ! -d "${ROOT}/.venv" ]]; then
  echo "info: .venv not found — running setup-python.sh"
  "${SCRIPT_DIR}/setup-python.sh"
fi

export UV_PROJECT_ENVIRONMENT="${ROOT}/.venv"

echo "info: pytest — packages/shared-logic"
uv run pytest packages/shared-logic/tests -q

echo "info: pytest — packages/test-fixtures"
uv run pytest packages/test-fixtures/tests -q

echo "info: packages Python unit tests passed"
