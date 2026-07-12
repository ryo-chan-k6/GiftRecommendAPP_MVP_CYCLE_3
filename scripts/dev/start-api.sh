#!/usr/bin/env bash
# api dev サーバを monorepo の pnpm script 経由で起動する（待受: http://localhost:3001）
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

usage() {
  cat <<'EOF'
Usage: ./scripts/dev/start-api.sh [--help]

Starts api via root package.json: pnpm dev:api
Default listen: http://localhost:3001 (API_BASE_URL in .env.example)

Prerequisites:
  - pnpm installed
  - .env present (./scripts/dev/copy-env-example.sh)
  - reco reachable when testing api → reco (start reco first)

Note: Express API（port 3001）。`apps/api` の `pnpm dev` をルート `dev:api` 経由で起動する。
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

if [[ -f "${ROOT}/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "${ROOT}/.env"
  set +a
else
  echo "warn: .env not found. Run ./scripts/dev/copy-env-example.sh and edit values."
fi

echo "info: starting api (pnpm dev:api) on http://localhost:3001"
exec pnpm dev:api
