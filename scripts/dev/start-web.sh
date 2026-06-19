#!/usr/bin/env bash
# web dev サーバを monorepo の pnpm script 経由で起動する（待受: http://localhost:3000）
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

usage() {
  cat <<'EOF'
Usage: ./scripts/dev/start-web.sh [--help]

Starts web via root package.json: pnpm dev:web
Default listen: http://localhost:3000 (NEXT_PUBLIC_API_BASE_URL → api on 3001)

Prerequisites:
  - pnpm installed
  - .env present (./scripts/dev/copy-env-example.sh)
  - api / reco running when testing browser → api flow

Note: apps/web dev script is a placeholder until Phase4 implementation.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

if ! command -v pnpm >/dev/null 2>&1; then
  echo "error: pnpm not found in PATH" >&2
  exit 1
fi

cd "${ROOT}"

if [[ ! -f "${ROOT}/package.json" ]]; then
  echo "error: package.json not found at repo root" >&2
  exit 1
fi

if [[ ! -f "${ROOT}/.env" ]]; then
  echo "warn: .env not found. Run ./scripts/dev/copy-env-example.sh and edit values."
fi

echo "info: starting web (pnpm dev:web) on http://localhost:3000"
exec pnpm dev:web
