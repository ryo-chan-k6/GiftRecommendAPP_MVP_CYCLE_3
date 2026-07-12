#!/usr/bin/env bash
# .env.example に定義された変数名が .env に含まれるか確認する（値は表示しない）
set -euo pipefail

STRICT=0
if [[ "${1:-}" == "--strict" ]]; then
  STRICT=1
fi

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
EXAMPLE="${ROOT}/.env.example"
ENV_FILE="${ROOT}/.env"

if [[ ! -f "${EXAMPLE}" ]]; then
  echo "error: .env.example not found at ${EXAMPLE}" >&2
  exit 1
fi

# .env.example から有効行の変数名を抽出（コメント行・空行を除外）
mapfile -t EXPECTED_KEYS < <(
  grep -E '^[A-Z][A-Z0-9_]*=' "${EXAMPLE}" | cut -d= -f1 | sort -u
)

echo "info: ${#EXPECTED_KEYS[@]} variable name(s) in .env.example (active lines)"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "warn: .env not found. Run ./scripts/dev/copy-env-example.sh first."
  if [[ "${STRICT}" -eq 1 ]]; then
    exit 1
  fi
  exit 0
fi

mapfile -t ENV_KEYS < <(
  grep -E '^[A-Z][A-Z0-9_]*=' "${ENV_FILE}" | cut -d= -f1 | sort -u
)

missing=0
for key in "${EXPECTED_KEYS[@]}"; do
  if ! printf '%s\n' "${ENV_KEYS[@]}" | grep -qx "${key}"; then
    echo "missing: ${key}"
    missing=$((missing + 1))
  fi
done

if [[ "${missing}" -gt 0 ]]; then
  echo "result: FAIL (${missing} missing in .env)"
  exit 1
fi

echo "result: OK (all .env.example active keys present in .env)"
exit 0
