#!/usr/bin/env bash
# supabase/.cli-version とインストール済み Supabase CLI の一致を確認する
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

db_require_repo_root
db_check_cli_version
