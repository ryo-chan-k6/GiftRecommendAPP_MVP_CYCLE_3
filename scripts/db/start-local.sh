#!/usr/bin/env bash
# ローカル Supabase スタックを起動する
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

db_require_repo_root
db_check_cli_version
echo "info: starting local Supabase stack..."
supabase start
