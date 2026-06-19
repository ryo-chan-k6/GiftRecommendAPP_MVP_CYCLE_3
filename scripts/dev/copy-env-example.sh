#!/usr/bin/env bash
# .env.example を .env にコピーする（既存 .env は上書きしない）
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
EXAMPLE="${ROOT}/.env.example"
TARGET="${ROOT}/.env"

if [[ ! -f "${EXAMPLE}" ]]; then
  echo "error: .env.example not found at ${EXAMPLE}" >&2
  exit 1
fi

if [[ -f "${TARGET}" ]]; then
  echo "skip: .env already exists (${TARGET}). Remove or edit manually."
  exit 0
fi

cp "${EXAMPLE}" "${TARGET}"
echo "created: ${TARGET} from .env.example"
echo "next: edit .env with local values (secrets are not committed to Git)"
