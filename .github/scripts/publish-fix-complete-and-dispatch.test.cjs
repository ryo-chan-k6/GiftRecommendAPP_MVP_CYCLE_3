"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const publish = require("./publish-fix-complete-and-dispatch.cjs");

const SAMPLE_COMMENT = `# Fix Review Comments Result

## 1. 対応結果

| 項目 | 内容 |
| ---- | ---- |
| Fix Outcome | \`ready_for_ai_review\` |
| 対象PR | \`#10\` |

## 12. Status更新意図

| 項目 | 内容 |
| ---- | ---- |
| 次Status | \`AI Review\` |
`;

test("resolveFixOutcome: コメントからFix Outcomeを抽出する", () => {
  const value = publish.resolveFixOutcome({ commentBody: SAMPLE_COMMENT });
  assert.equal(value, "ready_for_ai_review");
});

test("resolveFixOutcome: overrideが優先される", () => {
  const value = publish.resolveFixOutcome({
    commentBody: SAMPLE_COMMENT,
    fixOutcomeOverride: "split_required",
  });
  assert.equal(value, "split_required");
});

test("publishFixCompleteAndDispatch: dry_runではAPIを呼ばない", async () => {
  let called = 0;
  const result = await publish.publishFixCompleteAndDispatch({
    repository: "o/r",
    prNumber: 10,
    commentBody: SAMPLE_COMMENT,
    token: "t",
    dryRun: true,
    fetchImpl: async () => {
      called += 1;
    },
  });
  assert.equal(result.ok, true);
  assert.equal(result.fix_outcome, "ready_for_ai_review");
  assert.equal(called, 0);
});

test("publishFixCompleteAndDispatch: ready_for_ai_reviewはコメント投稿後にdispatchする", async () => {
  const calls = [];
  const result = await publish.publishFixCompleteAndDispatch({
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
  assert.equal(result.dispatch_skipped, false);
  assert.equal(calls.length, 2);
  assert.match(calls[0].url, /issues\/10\/comments$/);
  assert.match(calls[1].url, /dispatches$/);
});

test("publishFixCompleteAndDispatch: split_requiredはdispatchしない", async () => {
  const body = SAMPLE_COMMENT.replace("ready_for_ai_review", "split_required");
  let dispatchCalled = false;
  const result = await publish.publishFixCompleteAndDispatch({
    repository: "o/r",
    prNumber: 10,
    commentBody: body,
    token: "t",
    fetchImpl: async (url, options) => {
      if (url.includes("/dispatches")) dispatchCalled = true;
      if (url.includes("/issues/10/comments")) {
        return {
          ok: true,
          status: 201,
          json: async () => ({ html_url: "https://example.com/comment/1", id: 1 }),
        };
      }
      throw new Error(url);
    },
  });
  assert.equal(result.ok, true);
  assert.equal(result.dispatch_skipped, true);
  assert.equal(dispatchCalled, false);
});

test("publishFixCompleteAndDispatch: dispatch失敗時にrecoveryCommandを付与する", async () => {
  await assert.rejects(
    () =>
      publish.publishFixCompleteAndDispatch({
        repository: "o/r",
        prNumber: 10,
        commentBody: SAMPLE_COMMENT,
        commentFile: "/tmp/fix-complete.md",
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

test("verifyFixCompleteDispatch: dispatch済みならok", async () => {
  const result = await publish.verifyFixCompleteDispatch({
    repository: "o/r",
    prNumber: 10,
    token: "t",
    listComments: async () => [
      {
        body: SAMPLE_COMMENT,
        created_at: "2026-05-29T10:00:00Z",
        html_url: "https://example.com/c/1",
      },
    ],
    listRuns: async () => [
      {
        id: 99,
        display_title: "fix-ready · dispatch · PR #10 · ready_for_ai_review",
        created_at: "2026-05-29T10:00:05Z",
        status: "completed",
        conclusion: "success",
        html_url: "https://example.com/run/99",
      },
    ],
  });
  assert.equal(result.ok, true);
  assert.equal(result.dispatch_run_id, 99);
});
