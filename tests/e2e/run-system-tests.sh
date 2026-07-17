#!/usr/bin/env bash
# Layer2 システムテスト実行（test-system.yml から呼び出し）。
# infra / fixture は必須 pass。API 導線は既定で実行（SKIP_API_E2E=true で skip 可）。
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${ROOT}"

RESULTS_DIR="${RESULTS_DIR:-tests/e2e/results}"
REPORT_JSON="${RESULTS_DIR}/system-test-report.json"
REPORT_MD="${RESULTS_DIR}/system-test-report.md"
SKIP_API_E2E="${SKIP_API_E2E:-false}"
API_BASE_URL="${API_BASE_URL:-http://localhost:3001}"
RECO_BASE_URL="${RECO_BASE_URL:-http://localhost:8000}"
RECO_INTERNAL_API_KEY="${RECO_INTERNAL_API_KEY:-}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
DATABASE_URL="${DATABASE_URL:-}"

mkdir -p "${RESULTS_DIR}"

declare -a CASE_IDS=()
declare -a CASE_STATUSES=()
declare -a CASE_MESSAGES=()

passed=0
failed=0
skipped=0
phase4b_pending=0

record_case() {
  local id="$1"
  local status="$2"
  local message="$3"
  CASE_IDS+=("${id}")
  CASE_STATUSES+=("${status}")
  CASE_MESSAGES+=("${message}")
  case "${status}" in
    passed) passed=$((passed + 1)) ;;
    failed) failed=$((failed + 1)) ;;
    skipped) skipped=$((skipped + 1)) ;;
  esac
}

case_fixture_manifest() {
  local manifest="${ROOT}/tests/fixtures/manifest.json"
  if [[ ! -f "${manifest}" ]]; then
    record_case "fixture-manifest" "failed" "missing tests/fixtures/manifest.json"
    return
  fi
  local missing=0
  local path
  for path in \
    "tests/fixtures/api-input" \
    "supabase/seeds/test-data" \
    ".github/workflows/ci-db.yml" \
    ".github/workflows/test-system.yml"; do
    if [[ ! -e "${ROOT}/${path}" ]]; then
      missing=$((missing + 1))
      echo "error: manifest reference missing: ${path}" >&2
    fi
  done
  if [[ "${missing}" -gt 0 ]]; then
    record_case "fixture-manifest" "failed" "${missing} referenced path(s) missing"
  else
    record_case "fixture-manifest" "passed" "manifest.json and referenced paths exist"
  fi
}

case_db_connectivity() {
  if [[ -z "${DATABASE_URL}" ]]; then
    record_case "db-connectivity" "failed" "DATABASE_URL is not set"
    return
  fi
  if psql "${DATABASE_URL}" -c 'SELECT 1' >/dev/null 2>&1; then
    record_case "db-connectivity" "passed" "PostgreSQL SELECT 1 succeeded"
  else
    record_case "db-connectivity" "failed" "PostgreSQL unreachable"
  fi
}

case_db_test_seed() {
  if [[ -z "${DATABASE_URL}" ]]; then
    record_case "db-test-seed" "failed" "DATABASE_URL is not set"
    return
  fi
  local item_count feature_count
  item_count="$(psql "${DATABASE_URL}" -t -A -c "SELECT COUNT(*) FROM item WHERE external_item_code LIKE 'test-fixture-%'" 2>/dev/null || echo "0")"
  feature_count="$(psql "${DATABASE_URL}" -t -A -c "SELECT COUNT(*) FROM item_feature WHERE item_id IN (SELECT item_id FROM item WHERE external_item_code LIKE 'test-fixture-%')" 2>/dev/null || echo "0")"
  if [[ "${item_count}" -ge 3 && "${feature_count}" -ge 1 ]]; then
    record_case "db-test-seed" "passed" "test fixture items=${item_count} item_feature=${feature_count}"
  else
    record_case "db-test-seed" "failed" "expected test fixture rows (items>=3); got items=${item_count} item_feature=${feature_count}"
  fi
}

case_redis_connectivity() {
  if ! command -v redis-cli >/dev/null 2>&1; then
    record_case "redis-connectivity" "failed" "redis-cli not found"
    return
  fi
  local reply
  reply="$(redis-cli -u "${REDIS_URL}" PING 2>/dev/null || true)"
  if [[ "${reply}" == "PONG" ]]; then
    record_case "redis-connectivity" "passed" "Redis PING returned PONG"
  else
    record_case "redis-connectivity" "failed" "Redis unreachable via ${REDIS_URL}"
  fi
}

should_skip_api_cases() {
  if [[ "${SKIP_API_E2E}" == "1" || "${SKIP_API_E2E}" == "true" ]]; then
    return 0
  fi
  return 1
}

case_api_health() {
  if should_skip_api_cases; then
    record_case "api-health" "skipped" "SKIP_API_E2E enabled（infra 切り分け用）"
    phase4b_pending=1
    return
  fi
  local code
  code="$(curl -sS -o /dev/null -w "%{http_code}" --connect-timeout 2 --max-time 5 "${API_BASE_URL}/api/v1/health" 2>/dev/null || echo "000")"
  if [[ "${code}" == "200" ]]; then
    record_case "api-health" "passed" "GET /api/v1/health returned HTTP 200"
  else
    record_case "api-health" "failed" "GET /api/v1/health returned HTTP ${code}"
  fi
}

case_reco_health() {
  if should_skip_api_cases; then
    record_case "reco-health" "skipped" "SKIP_API_E2E enabled（infra 切り分け用）"
    return
  fi
  local headers=()
  if [[ -n "${RECO_INTERNAL_API_KEY}" ]]; then
    headers=(-H "X-Internal-Api-Key: ${RECO_INTERNAL_API_KEY}")
  fi
  local code
  code="$(curl -sS -o /dev/null -w "%{http_code}" --connect-timeout 2 --max-time 5 "${headers[@]}" "${RECO_BASE_URL}/internal/reco/v1/health" 2>/dev/null || echo "000")"
  if [[ "${code}" == "200" ]]; then
    record_case "reco-health" "passed" "GET /internal/reco/v1/health returned HTTP 200"
  else
    record_case "reco-health" "failed" "GET /internal/reco/v1/health returned HTTP ${code}"
  fi
}

case_recommendation_run() {
  if should_skip_api_cases; then
    record_case "recommendation-run" "skipped" "SKIP_API_E2E enabled（infra 切り分け用）"
    return
  fi
  local fixture="${ROOT}/tests/fixtures/api-input/recommendation-run-boss-thanks.json"
  if [[ ! -f "${fixture}" ]]; then
    record_case "recommendation-run" "failed" "missing fixture ${fixture}"
    return
  fi
  local body code
  body="$(jq 'del(.description)' "${fixture}")"
  code="$(curl -sS -o /tmp/recommendation-run-response.json -w "%{http_code}" \
    --connect-timeout 5 --max-time 120 \
    -H "Content-Type: application/json" \
    -X POST "${API_BASE_URL}/api/v1/recommendations" \
    -d "${body}" 2>/dev/null || echo "000")"
  if [[ "${code}" == "200" || "${code}" == "201" ]]; then
    record_case "recommendation-run" "passed" "POST /api/v1/recommendations returned HTTP ${code}"
  else
    record_case "recommendation-run" "failed" "POST /api/v1/recommendations returned HTTP ${code}"
  fi
}

case_fixture_manifest
case_db_connectivity
case_db_test_seed
case_redis_connectivity
case_api_health
case_reco_health
case_recommendation_run

if [[ "${SKIP_API_E2E}" == "1" || "${SKIP_API_E2E}" == "true" ]]; then
  phase4b_pending=1
fi

cases_json="[]"
for i in "${!CASE_IDS[@]}"; do
  cases_json="$(jq -cn \
    --argjson arr "${cases_json}" \
    --arg id "${CASE_IDS[$i]}" \
    --arg status "${CASE_STATUSES[$i]}" \
    --arg message "${CASE_MESSAGES[$i]}" \
    '$arr + [{id: $id, status: $status, message: $message}]')"
done

jq -n \
  --argjson cases "${cases_json}" \
  --argjson passed "${passed}" \
  --argjson failed "${failed}" \
  --argjson skipped "${skipped}" \
  --argjson phase4b_pending "$([[ "${phase4b_pending}" -eq 1 ]] && echo true || echo false)" \
  --argjson skip_api_e2e "$([[ "${SKIP_API_E2E}" == "1" || "${SKIP_API_E2E}" == "true" ]] && echo true || echo false)" \
  '{
    schemaVersion: "1.0",
    taskId: "task-gha-test-environment-test-system-workflow",
    issue: 676,
    phase4bPending: $phase4b_pending,
    skipApiE2e: $skip_api_e2e,
    summary: {passed: $passed, failed: $failed, skipped: $skipped},
    cases: $cases
  }' > "${REPORT_JSON}"

{
  echo "# System test report"
  echo ""
  echo "- passed: ${passed}"
  echo "- failed: ${failed}"
  echo "- skipped: ${skipped}"
  echo "- phase4b_pending: ${phase4b_pending}"
  echo ""
  echo "| id | status | message |"
  echo "| --- | --- | --- |"
  for i in "${!CASE_IDS[@]}"; do
    echo "| ${CASE_IDS[$i]} | ${CASE_STATUSES[$i]} | ${CASE_MESSAGES[$i]} |"
  done
} > "${REPORT_MD}"

echo "info: wrote ${REPORT_JSON}"
jq '.' "${REPORT_JSON}"

if [[ "${failed}" -gt 0 ]]; then
  echo "result: FAIL (${failed} case(s) failed)" >&2
  exit 1
fi

echo "result: OK (${passed} passed, ${skipped} skipped)"
exit 0
