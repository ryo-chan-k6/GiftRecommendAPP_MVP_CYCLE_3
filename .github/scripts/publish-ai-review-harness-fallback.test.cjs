"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fallback = require("./publish-ai-review-harness-fallback.cjs");

const SAMPLE_COMMENT = `# AI Review Result

## 1. レビュー結果

| 項目          | 内容                       |
| ------------- | -------------------------- |
| Review Result | \`approve_for_human_review\` |
| 対象PR        | \`#290\`                   |

## 22. Status更新意図

| 次Status   | \`Human Review\` |
`;

test("extractLatestAiReviewCommentFromTranscript: ログ prefix を除去して抽出", () => {
  const transcript = [
    "2026-05-31T15:30:00.3370233Z # AI Review Result",
    "2026-05-31T15:30:00.4419814Z | Review Result | `approve_for_human_review` |",
    "2026-05-31T15:30:00.8875036Z ## 22. Status更新意図",
    "2026-05-31T15:30:01.0707915Z ---",
  ].join("\n");
  const body = fallback.extractLatestAiReviewCommentFromTranscript(transcript);
  assert.match(body, /# AI Review Result/);
  assert.match(body, /approve_for_human_review/);
});

test("extractAiReviewCommentBlocks: 複数ブロックは最後を採用", () => {
  const transcript = `${SAMPLE_COMMENT.replace("approve_for_human_review", "request_changes")}\n---\n${SAMPLE_COMMENT}`;
  const blocks = fallback.extractAiReviewCommentBlocks(transcript);
  assert.equal(blocks.length, 2);
  assert.equal(
    fallback.extractLatestAiReviewCommentFromTranscript(transcript),
    blocks[1],
  );
});

test("publishAiReviewHarnessFallback: verify 済みなら skip", async () => {
  const result = await fallback.publishAiReviewHarnessFallback({
    repository: "o/r",
    prNumber: 290,
    sinceIso: "2026-05-31T15:27:52Z",
    token: "bot-token",
    transcriptText: SAMPLE_COMMENT,
    fetchImpl: async (url) => {
      if (url.includes("/issues/290/comments")) {
        return {
          ok: true,
          json: async () => [
            {
              body: SAMPLE_COMMENT,
              created_at: "2026-05-31T15:30:10Z",
              html_url: "https://example.com/c/1",
            },
          ],
        };
      }
      if (url.includes("/actions/workflows/pr-review-status-sync.yml/runs")) {
        return {
          ok: true,
          json: async () => ({
            workflow_runs: [
              {
                id: 1,
                display_title: "status-sync · dispatch · PR #290 · approve_for_human_review",
                created_at: "2026-05-31T15:30:15Z",
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

test("publishAiReviewHarnessFallback: transcript から publish する", async () => {
  const calls = [];
  const result = await fallback.publishAiReviewHarnessFallback({
    repository: "o/r",
    prNumber: 290,
    sinceIso: "2026-05-31T15:27:52Z",
    token: "bot-token",
    transcriptText: `2026-05-31T15:30:00Z ${SAMPLE_COMMENT.split("\n").join("\n2026-05-31T15:30:00Z ")}`,
    fetchImpl: async (url, options) => {
      calls.push({ url, method: options && options.method });
      if (url.includes("/issues/290/comments") && (!options || !options.method || options.method === "GET")) {
        return { ok: true, json: async () => [] };
      }
      if (url.includes("/issues/290/comments") && options.method === "POST") {
        return {
          ok: true,
          status: 201,
          json: async () => ({ html_url: "https://example.com/c/2", id: 2 }),
        };
      }
      if (url.includes("/dispatches")) {
        return { ok: true, status: 204, text: async () => "" };
      }
      if (url.includes("/actions/workflows/pr-review-status-sync.yml/runs")) {
        return { ok: true, json: async () => ({ workflow_runs: [] }) };
      }
      throw new Error(url);
    },
  });
  assert.equal(result.ok, true);
  assert.equal(result.reason, "published");
  assert.equal(calls.filter((c) => c.method === "POST").length, 2);
});
