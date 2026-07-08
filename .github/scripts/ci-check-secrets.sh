#!/usr/bin/env bash
# リポジトリ内の secret 実値混入を簡易検出する（MVP 品質ゲート）。
# 正本: CI・CD方針書 §9.2 secret-scan / 環境設計書 §19.8
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${ROOT}"

fail=0

echo "info: scanning tracked files for high-confidence secret patterns"

# プレースホルダ・正本ダミーは対象外
EXCLUDE_GLOB=(
  ':!.env.example'
  ':!docs/**'
  ':!prompts/templates/**'
  ':!**/*.md'
)

scan_pattern() {
  local label="$1"
  local pattern="$2"
  local matches
  matches="$(git grep -nE "${pattern}" -- "${EXCLUDE_GLOB[@]}" . 2>/dev/null || true)"
  if [[ -n "${matches}" ]]; then
    echo "error: possible ${label} detected:" >&2
    echo "${matches}" >&2
    fail=1
  fi
}

scan_pattern "GitHub PAT (ghp_)" 'ghp_[A-Za-z0-9]{36,}'
scan_pattern "GitHub fine-grained PAT" 'github_pat_[A-Za-z0-9_]{40,}'
scan_pattern "OpenAI API key (sk-)" 'sk-[A-Za-z0-9]{20,}'

# workflow 内の secret 直書き（${{ secrets.* }} 以外の疑い）
workflow_matches="$(git grep -nE '(api[_-]?key|token|password|secret)\s*[:=]\s*["'\''][^"'\'']{8,}["'\'']' -- .github/workflows/ 2>/dev/null \
  | grep -vE '\$\{\{\s*secrets\.' || true)"
if [[ -n "${workflow_matches}" ]]; then
  echo "error: possible hardcoded credential in workflow:" >&2
  echo "${workflow_matches}" >&2
  fail=1
fi

if [[ "${fail}" -ne 0 ]]; then
  echo "result: FAIL (secret scan)" >&2
  exit 1
fi

echo "result: OK (secret scan)"
