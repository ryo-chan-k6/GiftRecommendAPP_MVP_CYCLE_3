#!/usr/bin/env bash
# migration 適用済み DB に master seed のみ再投入する
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

db_require_repo_root
db_check_cli_version

if ! command -v psql >/dev/null 2>&1; then
  echo "error: psql not found in PATH" >&2
  exit 1
fi

DATABASE_URL="$(db_local_database_url)"
echo "info: applying master seed from supabase/seeds/masters/ ..."

while IFS= read -r file; do
  echo "info: ${file}"
  psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${file}"
done < <(db_seed_master_files)

echo "info: master seed apply complete"
