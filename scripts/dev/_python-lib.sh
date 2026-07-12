#!/usr/bin/env bash
# Shared helpers for Python dev scripts (uv + .python-version).
set -euo pipefail

python_lib_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}

python_lib_require_uv() {
  if ! command -v uv >/dev/null 2>&1; then
    echo "error: uv not found in PATH." >&2
    echo "Install: https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
  fi
}

python_lib_python_version() {
  local root="$1"
  if [[ -f "${root}/.python-version" ]]; then
    tr -d '[:space:]' < "${root}/.python-version"
  else
    echo "3.14"
  fi
}

python_lib_project_ready() {
  local project_dir="$1"
  [[ -f "${project_dir}/pyproject.toml" ]] \
    && grep -q '^\[project\]' "${project_dir}/pyproject.toml" 2>/dev/null
}

python_lib_reco_tests_ready() {
  local root="$1"
  [[ -d "${root}/apps/reco/tests/unit" ]] \
    && python_lib_project_ready "${root}/apps/reco"
}

python_lib_batch_tests_ready() {
  local root="$1"
  [[ -d "${root}/apps/batch/tests/unit" ]] \
    && python_lib_project_ready "${root}/apps/batch"
}
