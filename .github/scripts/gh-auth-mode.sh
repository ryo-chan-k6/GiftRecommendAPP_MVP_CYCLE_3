#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage (human/bot setup must be eval'd or sourced in the current shell):

  eval "$(bash .github/scripts/gh-auth-mode.sh human)"   # human mode ON
  eval "$(bash .github/scripts/gh-auth-mode.sh bot)"     # bot mode ON
  bash .github/scripts/gh-auth-mode.sh status              # show current mode

Optional shell functions (~/.bashrc):

  gra-human() { eval "$(bash REPO_ROOT/.github/scripts/gh-auth-mode.sh human)"; }
  gra-bot()   { eval "$(bash REPO_ROOT/.github/scripts/gh-auth-mode.sh bot)"; }
  gra-status(){ bash REPO_ROOT/.github/scripts/gh-auth-mode.sh status; }
EOF
}

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SCRIPT="$ROOT/.github/scripts/gh-bot-auth.cjs"

if [[ ! -f "$SCRIPT" ]]; then
  echo "gh-bot-auth.cjs not found: $SCRIPT" >&2
  exit 1
fi

case "${1:-}" in
  human)
    node "$SCRIPT" print-human-setup
    ;;
  bot)
    node "$SCRIPT" print-setup
    ;;
  status)
    node "$SCRIPT" status
    ;;
  help | -h | --help)
    usage
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
