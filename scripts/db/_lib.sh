#!/usr/bin/env bash
# scripts/db/ 共通ヘルパ（source 専用）

set -euo pipefail

db_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}

db_cli_version_file() {
  local root
  root="$(db_root)"
  echo "${root}/supabase/.cli-version"
}

db_expected_cli_version() {
  local file
  file="$(db_cli_version_file)"
  if [[ ! -f "${file}" ]]; then
    echo "error: missing ${file}" >&2
    return 1
  fi
  tr -d '[:space:]' < "${file}"
}

db_installed_cli_version() {
  if ! command -v supabase >/dev/null 2>&1; then
    echo "error: supabase CLI not found in PATH" >&2
    return 1
  fi
  supabase --version 2>/dev/null | head -n1 | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+'
}

db_check_cli_version() {
  local expected installed
  expected="$(db_expected_cli_version)"
  installed="$(db_installed_cli_version)"
  if [[ "${expected}" != "${installed}" ]]; then
    echo "error: Supabase CLI version mismatch (expected ${expected}, got ${installed})" >&2
    echo "info: pin file: $(db_cli_version_file)" >&2
    return 1
  fi
  echo "info: Supabase CLI ${installed} matches pin"
}

db_require_repo_root() {
  local root
  root="$(db_root)"
  if [[ ! -f "${root}/supabase/config.toml" ]]; then
    echo "error: supabase/config.toml not found (run from repository worktree)" >&2
    return 1
  fi
  cd "${root}"
}

db_local_database_url() {
  local url
  if url="$(supabase status -o env 2>/dev/null | sed -n 's/^DB_URL="\(.*\)"$/\1/p' | head -n1)" && [[ -n "${url}" ]]; then
    echo "${url}"
    return 0
  fi
  if url="$(supabase status 2>/dev/null | sed -n 's/.*DB URL: //p' | head -n1)" && [[ -n "${url}" ]]; then
    echo "${url}"
    return 0
  fi
  echo "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
}

db_seed_masters_dir() {
  echo "$(db_root)/supabase/seeds/masters"
}

db_seed_master_files() {
  local dir
  dir="$(db_seed_masters_dir)"
  if [[ ! -d "${dir}" ]]; then
    echo "error: missing ${dir}" >&2
    return 1
  fi
  find "${dir}" -maxdepth 1 -name '*.sql' -type f | sort
}
