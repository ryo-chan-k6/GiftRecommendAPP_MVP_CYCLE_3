"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const publish = require("./publish-ai-review-and-dispatch.cjs");

const SAMPLE_COMMENT = `# AI Review Result

## 1. レビュー結果

| 項目          | 内容                       |
| ------------- | -------------------------- |
| Review Result | \`approve_for_human_review\` |
| 対象PR        | \`#10\`                    |

## 22. Status更新意図

| 項目       | 内容           |
| ---------- | -------------- |
| 次Status   | \`Human Review\` |
`;

test("resolveReviewResult: コメントからReview Resultを抽出する", () => {
  const value = publish.resolveReviewResult({ commentBody: SAMPLE_COMMENT });
  assert.equal(value, "approve_for_human_review");
});

test("resolveReviewResult: overrideが優先される", () => {
  const value = publish.resolveReviewResult({
    commentBody: SAMPLE_COMMENT,
    reviewResultOverride: "request_changes",
  });
  assert.equal(value, "request_changes");
});

test("publishAiReviewAndDispatch: dry_runではAPIを呼ばない", async () => {
  let called = 0;
  const result = await publish.publishAiReviewAndDispatch({
    repository: "o/r",
    prNumber: 10,
    commentBody: SAMPLE_COMMENT,
    token: "t",
    dryRun: true,
    fetchImpl: async () => {
      called += 1;
      return { ok: true, json: async () => ({}) };
    },
  });
  assert.equal(result.ok, true);
  assert.equal(result.review_result, "approve_for_human_review");
  assert.equal(called, 0);
});

test("publishAiReviewAndDispatch: コメント投稿後にdispatchする", async () => {
  const calls = [];
  const result = await publish.publishAiReviewAndDispatch({
    repository: "o/r",
    prNumber: 10,
    commentBody: SAMPLE_COMMENT,
    token: "t",
    fetchImpl: async (url, options) => {
      calls.push({ url, method: options.method });
      if (url.includes("/issues/10/comments") && options.method === "POST") {
        return {
          ok: true,
          status: 201,
          json: async () => ({ html_url: "https://example.com/comment/1", id: 1 }),
        };
      }
      if (url.includes("/dispatches")) {
        return { ok: true, status: 204, async text() { return ""; } };
      }
      throw new Error(`unexpected url: ${url}`);
    },
  });
  assert.equal(result.ok, true);
  assert.equal(calls.length, 2);
  assert.match(calls[0].url, /issues\/10\/comments$/);
  assert.match(calls[1].url, /dispatches$/);
});

test("publishAiReviewAndDispatch: dispatch失敗時にrecoveryCommandを付与する", async () => {
  await assert.rejects(
    () =>
      publish.publishAiReviewAndDispatch({
        repository: "o/r",
        prNumber: 10,
        commentBody: SAMPLE_COMMENT,
        commentFile: "/tmp/ai-review.md",
        token: "t",
        fetchImpl: async (url, options) => {
          if (url.includes("/issues/10/comments")) {
            return {
              ok: true,
              status: 201,
              json: async () => ({ html_url: "https://example.com/comment/1", id: 1 }),
            };
          }
          if (url.includes("/dispatches")) {
            return { ok: false, status: 403, text: async () => "forbidden" };
          }
          throw new Error(url);
        },
      }),
    (error) => {
      assert.match(error.message, /dispatch failed/i);
      assert.match(error.recoveryCommand, /--dispatch-only/);
      assert.match(error.recoveryCommand, /--comment-file/);
      return true;
    },
  );
});

test("verifyAiReviewDispatch: dispatch済みならok", async () => {
  const result = await publish.verifyAiReviewDispatch({
    repository: "o/r",
    prNumber: 10,
    token: "t",
    listComments: async () => [
      {
        body: SAMPLE_COMMENT,
        created_at: "2026-05-30T00:00:00Z",
        html_url: "https://example.com/c/1",
      },
    ],
    listRuns: async () => [
      {
        id: 99,
        display_title: "status-sync · dispatch · PR #10 · approve_for_human_review",
        created_at: "2026-05-30T00:00:05Z",
        status: "completed",
        conclusion: "success",
        html_url: "https://example.com/run/99",
      },
    ],
  });
  assert.equal(result.ok, true);
  assert.equal(result.dispatch_run_id, 99);
});

test("verifyAiReviewDispatch: コメントのみでdispatch欠落", async () => {
  const result = await publish.verifyAiReviewDispatch({
    repository: "o/r",
    prNumber: 10,
    token: "t",
    listComments: async () => [
      {
        body: SAMPLE_COMMENT,
        created_at: "2026-05-30T00:00:00Z",
        html_url: "https://example.com/c/1",
      },
    ],
    listRuns: async () => [],
  });
  assert.equal(result.ok, false);
  assert.equal(result.reason, "dispatch_missing");
  assert.match(result.recovery_command, /--dispatch-only/);
});

test("verifyAiReviewDispatch: AI Reviewコメントなし", async () => {
  const result = await publish.verifyAiReviewDispatch({
    repository: "o/r",
    prNumber: 10,
    token: "t",
    listComments: async () => [{ body: "hello", created_at: "2026-05-30T00:00:00Z" }],
    listRuns: async () => [],
  });
  assert.equal(result.ok, false);
  assert.equal(result.reason, "no_ai_review_comment");
});
