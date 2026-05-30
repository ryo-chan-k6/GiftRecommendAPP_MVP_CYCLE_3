#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "== 1. Unit tests =="
node --test \
  .github/scripts/slack-notify.test.cjs \
  .github/scripts/dispatch-pr-ready-for-ai-review.test.cjs \
  .github/scripts/publish-fix-complete-and-dispatch.test.cjs

echo ""
echo "== 2. Template parse (fix-complete-comment.md) =="
node - <<'NODE'
const fs = require("fs");
const slack = require("./.github/scripts/slack-notify.cjs");
const template = fs.readFileSync("prompts/templates/review/fix-complete-comment.md", "utf8");
const sample = template
  .replace(/#<PR番号>/g, "#9999")
  .replace(/#<Issue番号>/g, "#265")
  .replace(/<branch名>/g, "test/verify")
  .replace(/@<review-definition>/g, "@prompts/definitions/_examples/review-definition.example.yaml")
  .replace(/#<PR番号>/g, "#9999");
if (!slack.isFixCompleteResultComment(sample)) {
  throw new Error("Template is not recognized as fix-complete comment");
}
const extracted = slack.extractFixOutcomeFromComment(sample);
if (!extracted.ok || extracted.value !== "ready_for_ai_review") {
  throw new Error(`Unexpected Fix Outcome: ${JSON.stringify(extracted)}`);
}
console.log("OK: template -> ready_for_ai_review");
NODE

echo ""
echo "== 3. dry-run: ready_for_ai_review (comment + dispatch) =="
COMMENT_FILE="$ROOT/.tmp-fix-complete-comment-verify.md"
if [[ ! -f "$COMMENT_FILE" ]]; then
  echo "WARN: $COMMENT_FILE missing; using inline sample"
  COMMENT_FILE=""
fi
export GH_TOKEN="${GH_TOKEN:-dry-run-test}"
if [[ -n "$COMMENT_FILE" ]]; then
  node .github/scripts/publish-fix-complete-and-dispatch.cjs \
    --repository ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3 \
    --pr 9999 \
    --comment-file "$COMMENT_FILE" \
    --dry-run | node -e "const j=JSON.parse(require('fs').readFileSync(0,'utf8')); if(!j.ok||j.dispatch_skipped||j.fix_outcome!=='ready_for_ai_review'){process.exit(1)} console.log('OK: dispatch planned for', j.fix_outcome);"
else
  echo "SKIP file-based dry-run"
fi

echo ""
echo "== 4. dry-run: split_required (dispatch skipped) =="
node - <<'NODE'
const fs = require("fs");
const publish = require("./.github/scripts/publish-fix-complete-and-dispatch.cjs");
const body = fs.readFileSync(".tmp-fix-complete-comment-verify.md", "utf8").replace(/ready_for_ai_review/g, "split_required");
publish.publishFixCompleteAndDispatch({
  repository: "ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3",
  prNumber: 9999,
  commentBody: body,
  token: "dry-run-test",
  dryRun: true,
}).then((result) => {
  if (!result.ok || !result.dispatch_skipped || result.fix_outcome !== "split_required") {
    console.error(JSON.stringify(result, null, 2));
    process.exit(1);
  }
  console.log("OK: split_required skipped dispatch");
});
NODE

echo ""
echo "== 5. Workflow file exists =="
test -f .github/workflows/pr-ready-for-ai-review.yml
grep -q "fix_ready_for_ai_review" .github/workflows/pr-ready-for-ai-review.yml
grep -q "expectedCurrentStatusForFixComplete" .github/workflows/pr-ready-for-ai-review.yml
echo "OK: workflow triggers and status guard present"

echo ""
echo "== 6. Remote workflow registration (optional) =="
if command -v gh >/dev/null 2>&1; then
  if gh workflow list --repo ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3 2>/dev/null | grep -qi "ready for ai review"; then
    echo "OK: workflow registered on GitHub remote"
  else
    echo "SKIP: workflow not yet on remote (merge/push required for live E2E)"
  fi
else
  echo "SKIP: gh not available"
fi

echo ""
echo "ALL LOCAL VERIFICATION PASSED"
