#!/usr/bin/env bash
# ローカル DB を migration + master seed までリセットする
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

db_require_repo_root
db_check_cli_version
echo "info: resetting local database (migrations + master seed)..."
echo "warning: this destroys local DB data. Do not run against prod/cloud."
supabase db reset
