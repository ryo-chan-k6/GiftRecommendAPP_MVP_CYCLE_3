#!/usr/bin/env bash
# supabase/migrations/ の未適用 migration を適用する
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

db_require_repo_root
db_check_cli_version
echo "info: applying migrations from supabase/migrations/..."
supabase migration up
