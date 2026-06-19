#!/usr/bin/env bash
# Redis ローカルコンテナを docker compose で起動する
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
COMPOSE_FILE="${ROOT}/docker-compose.dev.yml"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "error: docker-compose.dev.yml not found at ${COMPOSE_FILE}" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "error: docker not found in PATH (Docker Desktop required)" >&2
  exit 1
fi

cd "${ROOT}"
docker compose -f docker-compose.dev.yml up -d redis
echo "info: Redis started (default REDIS_URL: redis://localhost:6379/0 per .env.example)"
