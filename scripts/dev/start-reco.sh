#!/usr/bin/env bash
# reco dev サーバを monorepo の pnpm script 経由で起動する（待受: http://localhost:8000）
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

usage() {
  cat <<'EOF'
Usage: ./scripts/dev/start-reco.sh [--help]

Starts reco via root package.json: pnpm dev:reco
Default listen: http://localhost:8000 (RECO_BASE_URL in .env.example)

Prerequisites:
  - pnpm installed
  - .env present (./scripts/dev/copy-env-example.sh)
  - PostgreSQL / Redis reachable (§7 in ローカル開発手順書)

Note: FastAPI + uvicorn（port 8000）。`apps/reco` の `pnpm dev` をルート `dev:reco` 経由で起動する。
  Requires: uv、apps/reco 依存（./scripts/dev/setup-python-reco.sh）、.env（RECO_INTERNAL_API_KEY / DATABASE_URL）
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

echo "info: starting reco (pnpm dev:reco) on http://localhost:8000"
exec pnpm dev:reco
