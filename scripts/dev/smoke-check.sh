#!/usr/bin/env bash
# ローカル疎通チェック: env 変数名 / PostgreSQL / Redis / app health（Phase4 まで health 成功は optional）
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SKIP_ENV=0
SKIP_DB=0
SKIP_REDIS=0
SKIP_APPS=0

usage() {
  cat <<'EOF'
Usage: ./scripts/dev/smoke-check.sh [options]

Runs staged local smoke checks from repository root:
  1. Environment variable names (check-env-names.sh --strict)
  2. PostgreSQL (psql SELECT 1 via DATABASE_URL)
  3. Redis (redis-cli PING via REDIS_URL)
  4. App health (reco / api / web — optional until Phase4)

Options:
  --skip-env     Skip environment variable name check
  --skip-db      Skip PostgreSQL check
  --skip-redis   Skip Redis check
  --skip-apps    Skip app health checks (recommended during Phase3b placeholder)
  -h, --help     Show this help

Notes:
  - Loads .env from repo root when present (values are never printed).
  - Redis: uses redis-cli when in PATH; otherwise PING via docker compose exec on running redis service.
  - App health failures do not fail the script in Phase3b (placeholder / not started).
  - See docs/06_実装設計/cross_cutting/ローカル開発手順書.md §10.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-env) SKIP_ENV=1 ;;
    --skip-db) SKIP_DB=1 ;;
    --skip-redis) SKIP_REDIS=1 ;;
    --skip-apps) SKIP_APPS=1 ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

cd "${ROOT}"

load_dotenv() {
  if [[ -f "${ROOT}/.env" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "${ROOT}/.env"
    set +a
  fi
}

load_dotenv

failures=0
step=0
total=4

run_step() {
  step=$((step + 1))
  echo ""
  echo "==> [${step}/${total}] $1"
}

# --- 1. Environment variable names ---
if [[ "${SKIP_ENV}" -eq 0 ]]; then
  run_step "Environment variable names"
  if bash "${ROOT}/scripts/dev/check-env-names.sh" --strict; then
    echo "ok: environment variable names"
  else
    echo "fail: environment variable names (run ./scripts/dev/copy-env-example.sh and edit .env)" >&2
    failures=$((failures + 1))
  fi
else
  echo "skip: environment variable names (--skip-env)"
fi

require_var() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "fail: ${name} is not set in .env" >&2
    return 1
  fi
  return 0
}

# redis-cli が PATH にない場合、docker-compose.dev.yml の redis コンテナ経由で PING する
redis_ping() {
  local url="${1:-}"
  local reply=""

  if command -v redis-cli >/dev/null 2>&1; then
    reply="$(redis-cli -u "${url}" PING 2>/dev/null || true)"
    printf '%s' "${reply}"
    return 0
  fi

  local compose_file="${ROOT}/docker-compose.dev.yml"
  if [[ -f "${compose_file}" ]] && command -v docker >/dev/null 2>&1; then
    if docker compose -f "${compose_file}" ps --status running --services 2>/dev/null | grep -qx redis; then
      reply="$(docker compose -f "${compose_file}" exec -T redis redis-cli PING 2>/dev/null || true)"
      printf '%s' "${reply}"
      return 0
    fi
  fi

  return 1
}

# --- 2. PostgreSQL ---
if [[ "${SKIP_DB}" -eq 0 ]]; then
  run_step "PostgreSQL"
  if ! command -v psql >/dev/null 2>&1; then
    echo "fail: psql not found in PATH" >&2
    failures=$((failures + 1))
  elif ! require_var DATABASE_URL; then
    failures=$((failures + 1))
  elif psql "${DATABASE_URL}" -c 'SELECT 1' >/dev/null 2>&1; then
    echo "ok: PostgreSQL (SELECT 1)"
  else
    echo "fail: PostgreSQL unreachable (start local DB — see DB構築手順書)" >&2
    failures=$((failures + 1))
  fi
else
  echo "skip: PostgreSQL (--skip-db)"
fi

# --- 3. Redis ---
if [[ "${SKIP_REDIS}" -eq 0 ]]; then
  run_step "Redis"
  if ! require_var REDIS_URL; then
    failures=$((failures + 1))
  elif ! redis_ping "${REDIS_URL}" >/dev/null; then
    echo "fail: redis-cli not found and Redis container not running (install redis-cli or run ./scripts/dev/start-redis.sh)" >&2
    failures=$((failures + 1))
  else
    redis_reply="$(redis_ping "${REDIS_URL}")"
    if [[ "${redis_reply}" == "PONG" ]]; then
      if command -v redis-cli >/dev/null 2>&1; then
        echo "ok: Redis (PONG via redis-cli)"
      else
        echo "ok: Redis (PONG via docker compose exec redis)"
      fi
    else
      echo "fail: Redis unreachable (run ./scripts/dev/start-redis.sh)" >&2
      failures=$((failures + 1))
    fi
  fi
else
  echo "skip: Redis (--skip-redis)"
fi

# --- 4. App health (Phase4 まで optional — 接続不可は skip 扱い) ---
check_http_health() {
  local name="$1"
  local url="$2"
  shift 2
  local curl_args=(-sS -o /dev/null -w "%{http_code}" --connect-timeout 2 --max-time 5)
  local code

  while [[ $# -gt 0 ]]; do
    curl_args+=("$1")
    shift
  done

  if ! code="$(curl "${curl_args[@]}" "${url}" 2>/dev/null)"; then
    echo "skip: ${name} not listening (${url}) — Phase4 placeholder or app not started"
    return 0
  fi

  if [[ "${code}" == "200" ]]; then
    echo "ok: ${name} health (HTTP ${code})"
  else
    echo "skip: ${name} health returned HTTP ${code} (Phase4 implementation pending — not a failure in Phase3b)"
  fi
}

if [[ "${SKIP_APPS}" -eq 0 ]]; then
  run_step "App health (optional until Phase4)"
  reco_headers=()
  if [[ -n "${RECO_INTERNAL_API_KEY:-}" ]]; then
    reco_headers=(-H "X-Internal-Api-Key: ${RECO_INTERNAL_API_KEY}")
  fi
  check_http_health "reco" "http://localhost:8000/internal/reco/v1/health" "${reco_headers[@]}"
  check_http_health "api" "http://localhost:3001/api/v1/health"
  check_http_health "web" "http://localhost:3000/"
else
  echo "skip: app health (--skip-apps)"
fi

echo ""
if [[ "${failures}" -gt 0 ]]; then
  echo "result: FAIL (${failures} required check(s) failed)"
  exit 1
fi

echo "result: OK (required checks passed; app health skips are expected before Phase4)"
exit 0
