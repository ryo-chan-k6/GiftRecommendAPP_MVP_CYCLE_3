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

test("extractLatestFixCompleteCommentFromTranscript: テンプレート全文をログ prefix 付きで抽出", () => {
  const transcript = [
    "2026-06-04T07:43:39.0581671Z # Fix Review Comments Result",
    "2026-06-04T07:43:39.0886163Z",
    "2026-06-04T07:43:39.0886163Z ## 1. 対応結果",
    "2026-06-04T07:43:39.3669029Z | Fix Outcome | `ready_for_ai_review` |",
    "2026-06-04T07:43:39.7288016Z | 対象PR | `#359` |",
    "2026-06-04T07:43:46.4693163Z ## 12. Status更新意図",
    "2026-06-04T07:43:46.5199719Z | 次Status | `AI Review` |",
    "2026-06-04T07:43:46.5199719Z ---",
  ].join("\n");
  const body = fallback.extractLatestFixCompleteCommentFromTranscript(transcript, {
    prNumber: 359,
  });
  assert.match(body, /Fix Review Comments Result/);
  assert.match(body, /ready_for_ai_review/);
  assert.doesNotMatch(body, /harness-fallback: synthesized/);
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

test("extractPrBodyUpdateFromTranscript: PR本文セクションを抽出", () => {
  const transcript = `## PR本文（更新後全文）

## Summary

Related to #458

# Fix Review Comments Result

## 1. 対応結果
`;
  const body = fallback.extractPrBodyUpdateFromTranscript(transcript);
  assert.match(body, /Related to #458/);
  assert.doesNotMatch(body, /Fix Review Comments Result/);
});

test("prBodyNeedsTaskIssueReferenceUpdate: Closes のみなら true", () => {
  assert.equal(fallback.prBodyNeedsTaskIssueReferenceUpdate("Summary\n\nCloses #458\n"), true);
  assert.equal(
    fallback.prBodyNeedsTaskIssueReferenceUpdate("Related to #458\n"),
    false,
  );
});

test("publishFixCompleteHarnessFallback: PR本文を更新してから publish", async () => {
  const updatedBody = "## Summary\n\nRelated to #458\n";
  const transcript = `## PR本文（更新後全文）

${updatedBody}
${COMMAND_OUTPUT}`;
  const calls = [];
  const result = await fallback.publishFixCompleteHarnessFallback({
    repository: "o/r",
    prNumber: 359,
    token: "bot-token",
    transcriptText: transcript,
    fetchImpl: async (url, options) => {
      calls.push({ url, method: options && options.method });
      if (url.includes("/pulls/359") && (!options || !options.method || options.method === "GET")) {
        return {
          ok: true,
          json: async () => ({ body: "Closes #358\n" }),
        };
      }
      if (url.includes("/pulls/359") && options.method === "PATCH") {
        return { ok: true, json: async () => ({ body: updatedBody }) };
      }
      if (url.includes("/issues/359/comments") && (!options || !options.method || options.method === "GET")) {
        return { ok: true, json: async () => [] };
      }
      if (url.includes("/issues/359/comments") && options.method === "POST") {
        return {
          ok: true,
          status: 201,
          json: async () => ({ html_url: "https://example.com/c/3", id: 3 }),
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
  assert.equal(result.reason, "published");
  assert.equal(result.pr_body_update.reason, "pr_body_updated");
  assert.ok(calls.some((c) => c.method === "PATCH" && c.url.includes("/pulls/359")));
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
