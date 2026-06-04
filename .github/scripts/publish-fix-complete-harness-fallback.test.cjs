"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fallback = require("./publish-fix-complete-harness-fallback.cjs");

const SAMPLE_COMMENT = `# Fix Review Comments Result

## 1. 対応結果

| 項目 | 内容 |
| ---- | ---- |
| Fix Outcome | \`ready_for_ai_review\` |
| 対象PR | \`#359\` |

## 12. Status更新意図

| 項目 | 内容 |
| ---- | ---- |
| 次Status | \`AI Review\` |
`;

const COMMAND_OUTPUT = `## fix-review-comments 実行結果

### Fix Outcome
\`ready_for_ai_review\`

### 対象PR
https://github.com/example/pull/359
`;

test("extractLatestFixCompleteCommentFromTranscript: テンプレート形式を抽出", () => {
  const body = fallback.extractLatestFixCompleteCommentFromTranscript(SAMPLE_COMMENT, {
    prNumber: 359,
  });
  assert.match(body, /Fix Review Comments Result/);
  assert.match(body, /ready_for_ai_review/);
});

test("extractLatestFixCompleteCommentFromTranscript: Command 出力形式から合成", () => {
  const body = fallback.extractLatestFixCompleteCommentFromTranscript(COMMAND_OUTPUT, {
    prNumber: 359,
  });
  assert.match(body, /Fix Review Comments Result/);
  assert.match(body, /ready_for_ai_review/);
  assert.match(body, /harness-fallback: synthesized/);
});

test("publishFixCompleteHarnessFallback: verify 済みなら skip", async () => {
  const result = await fallback.publishFixCompleteHarnessFallback({
    repository: "o/r",
    prNumber: 359,
    token: "bot-token",
    transcriptText: SAMPLE_COMMENT,
    fetchImpl: async (url) => {
      if (url.includes("/issues/359/comments")) {
        return {
          ok: true,
          json: async () => [
            {
              body: SAMPLE_COMMENT,
              created_at: "2026-06-04T07:44:00Z",
              html_url: "https://example.com/c/1",
            },
          ],
        };
      }
      if (url.includes("/actions/workflows/pr-ready-for-ai-review.yml/runs")) {
        return {
          ok: true,
          json: async () => ({
            workflow_runs: [
              {
                id: 1,
                display_title: "fix-ready · dispatch · PR #359",
                created_at: "2026-06-04T07:45:00Z",
                status: "completed",
                conclusion: "success",
              },
            ],
          }),
        };
      }
      throw new Error(url);
    },
  });
  assert.equal(result.ok, true);
  assert.equal(result.skipped, true);
  assert.equal(result.reason, "already_published");
});

test("publishFixCompleteHarnessFallback: transcript から publish する", async () => {
  const calls = [];
  const result = await fallback.publishFixCompleteHarnessFallback({
    repository: "o/r",
    prNumber: 359,
    token: "bot-token",
    transcriptText: COMMAND_OUTPUT,
    fetchImpl: async (url, options) => {
      calls.push({ url, method: options && options.method });
      if (url.includes("/issues/359/comments") && (!options || !options.method || options.method === "GET")) {
        return { ok: true, json: async () => [] };
      }
      if (url.includes("/issues/359/comments") && options.method === "POST") {
        return {
          ok: true,
          status: 201,
          json: async () => ({ html_url: "https://example.com/c/2", id: 2 }),
        };
      }
      if (url.includes("/dispatches")) {
        return { ok: true, status: 204, text: async () => "" };
      }
      if (url.includes("/actions/workflows/pr-ready-for-ai-review.yml/runs")) {
        return { ok: true, json: async () => ({ workflow_runs: [] }) };
      }
      throw new Error(`unexpected: ${url}`);
    },
  });
  assert.equal(result.ok, true);
  assert.equal(result.skipped, false);
  assert.equal(result.reason, "published");
  assert.equal(result.synthesized, true);
  const postCalls = calls.filter((c) => c.method === "POST");
  assert.ok(postCalls.length >= 1);
  assert.ok(postCalls.some((c) => c.url.includes("/issues/359/comments")));
});

test("publishFixCompleteHarnessFallback: ready_for_ai_review 以外は publish しない", async () => {
  const transcript = `${SAMPLE_COMMENT.replace("ready_for_ai_review", "split_required")}`;
  const result = await fallback.publishFixCompleteHarnessFallback({
    repository: "o/r",
    prNumber: 10,
    token: "bot-token",
    transcriptText: transcript,
    fetchImpl: async (url) => {
      if (url.includes("/issues/10/comments")) {
        return { ok: true, json: async () => [] };
      }
      if (url.includes("/actions/workflows/pr-ready-for-ai-review.yml/runs")) {
        return { ok: true, json: async () => ({ workflow_runs: [] }) };
      }
      throw new Error(url);
    },
  });
  assert.equal(result.ok, true);
  assert.equal(result.skipped, true);
  assert.equal(result.reason, "fix_outcome_not_ready_for_ai_review");
});
