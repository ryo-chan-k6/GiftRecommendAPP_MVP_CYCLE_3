#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(diname "$0")/../.." && pwd)"
cd "$ROOT"

CONFIG_JSON="$(node -e "const c=require('./.github/ai-bot-account.json'); console.log([c.machine_account_login,c.repository||'ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3'].join('|'))")"
BOT_USER="${CONFIG_JSON%%|*}"
REPO="${CONFIG_JSON#*|}"
BRANCH="test/bot-author-human-review-e2e"
BASE="develop"

node .github/scripts/gh-bot-auth.cjs verify
eval "$(node .github/scripts/gh-bot-auth.cjs print-setup)"
GIT_USER_JSON="$(node .github/scripts/gh-bot-auth.cjs print-git-user)"
GIT_NAME="$(node -e "console.log(JSON.parse(process.argv[1]).name)" "$GIT_USER_JSON")"
GIT_EMAIL="$(node -e "console.log(JSON.parse(process.argv[1]).email)" "$GIT_USER_JSON")"

TOKEN="${GH_BOT_TOKEN:?GH_BOT_TOKEN is required}"

git fetch origin "$BASE"
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git checkout "$BRANCH"
else
  git checkout -B "$BRANCH" "origin/$BASE"
fi

git add ai-logs/experiments/2026-05-30-bot-author-human-review-e2e.md
if git diff --cached --quiet; then
  echo "No staged changes (file may already be committed)."
else
  git -c "user.name=$GIT_NAME" -c "user.email=$GIT_EMAIL" commit -m "$(cat <<EOF
test: bot author Human Review E2E用マーカー

${BOT_USER} が PR author になることを確認する。
EOF
)"
fi

git push "https://x-access-token:${TOKEN}@github.com/${REPO}.git" "HEAD:${BRANCH}"

PR_URL="$(gh pr create \
  --repo "$REPO" \
  --base "$BASE" \
  --head "$BRANCH" \
  --title "test: bot author Human Review E2E" \
  --body "$(cat <<EOF
## 概要

\`${BOT_USER}\` が PR author となり、\`ryo-chan-k6\` が Human Review（Approve / Request changes）できることを確認する E2E 用 PR。

## 確認手順

1. PR author が \`${BOT_USER}\` であること
2. \`ryo-chan-k6\` で Review changes → Approve / Request changes が選択できること

## 後片付け

検証後 Close 可（merge 不要）。
EOF
)")"

PR_NUM="$(gh pr view "$PR_URL" --json number --jq .number)"
AUTHOR="$(gh pr view "$PR_NUM" --repo "$REPO" --json author --jq .author.login)"

echo ""
echo "PR: $PR_URL"
echo "PR number: #$PR_NUM"
echo "Author: $AUTHOR"

if [[ "$AUTHOR" != "$BOT_USER" ]]; then
  echo "ERROR: PR author is not $BOT_USER" >&2
  exit 1
fi

echo "SUCCESS: PR author is $BOT_USER. Human Review test on GitHub Web as ryo-chan-k6."
