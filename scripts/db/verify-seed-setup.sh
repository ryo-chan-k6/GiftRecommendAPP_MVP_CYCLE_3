#!/usr/bin/env bash
# supabase/seeds/masters と config.toml [db.seed] の正本整合を検証する
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

db_require_repo_root

errors=0

config_file="$(db_root)/supabase/config.toml"
masters_dir="$(db_root)/supabase/seeds/masters"
legacy_dir="$(db_root)/db/seeds"

if [[ ! -f "${config_file}" ]]; then
  echo "error: missing ${config_file}" >&2
  errors=$((errors + 1))
elif ! grep -q '^\[db\.seed\]' "${config_file}" || ! grep -q './seeds/masters/\*\.sql' "${config_file}"; then
  echo "error: [db.seed] sql_paths must include ./seeds/masters/*.sql in ${config_file}" >&2
  errors=$((errors + 1))
fi

if [[ -d "${legacy_dir}" ]]; then
  echo "error: legacy directory still exists: ${legacy_dir} (remove after migration to supabase/seeds/)" >&2
  errors=$((errors + 1))
fi

if [[ ! -d "${masters_dir}" ]]; then
  echo "error: missing ${masters_dir}" >&2
  errors=$((errors + 1))
else
  count="$(find "${masters_dir}" -maxdepth 1 -name '*.sql' -type f | wc -l | tr -d ' ')"
  if [[ "${count}" -lt 1 ]]; then
    echo "error: no master seed SQL files in ${masters_dir}" >&2
    errors=$((errors + 1))
  else
    echo "info: found ${count} master seed file(s) in supabase/seeds/masters/"
  fi
fi

if [[ "${errors}" -gt 0 ]]; then
  exit 1
fi

echo "info: seed setup verification passed"
