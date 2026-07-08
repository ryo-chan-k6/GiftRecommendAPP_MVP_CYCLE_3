#!/usr/bin/env bash
# Apply test-data seed SQL (Layer2 fixture DB state).
# NOT included in supabase db reset — run explicitly after master seed.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/db/_lib.sh
source "${ROOT}/scripts/db/_lib.sh"

db_require_repo_root
db_check_cli_version

SEED_DIR="${ROOT}/supabase/seeds/test-data"
DATABASE_URL="${DATABASE_URL:-$(db_local_database_url)}"

if [[ ! -d "${SEED_DIR}" ]]; then
  echo "error: missing ${SEED_DIR}" >&2
  exit 1
fi

shopt -s nullglob
files=("${SEED_DIR}"/*.sql)
shopt -u nullglob

if [[ ${#files[@]} -eq 0 ]]; then
  echo "error: no SQL files in ${SEED_DIR}" >&2
  exit 1
fi

echo "info: applying test-data seed from ${SEED_DIR}"
for sql_file in "${files[@]}"; do
  echo "info: psql ${sql_file}"
  psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${sql_file}"
done

item_count="$(psql "${DATABASE_URL}" -t -A -c "SELECT COUNT(*) FROM item WHERE external_item_code LIKE 'test-fixture-%'")"
feature_count="$(psql "${DATABASE_URL}" -t -A -c "SELECT COUNT(*) FROM item_feature WHERE item_id IN (SELECT item_id FROM item WHERE external_item_code LIKE 'test-fixture-%')")"
echo "info: test-data seed verification passed (items=${item_count}, item_feature rows=${feature_count})"
