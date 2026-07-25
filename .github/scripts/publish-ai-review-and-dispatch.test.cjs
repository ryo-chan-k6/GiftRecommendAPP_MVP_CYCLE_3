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

const TRUNCATED_COMMENT = `# AI Review Result

## 1. レビュー結果

| 項目          | 内容                       |
| ------------- | -------------------------- |
| Review Result | \`approve_for_human_review\` |
| 対象PR        | \`302\`                    |
...

（全文は \`/tmp/ai-review-comment-302.md\` を参照）
`;

test("isTruncatedAiReviewComment: ローカルファイル参照/省略を検出する", () => {
  assert.equal(publish.isTruncatedAiReviewComment(TRUNCATED_COMMENT), true);
  assert.equal(publish.isTruncatedAiReviewComment(SAMPLE_COMMENT), false);
});

test("isTruncatedAiReviewComment: 全文参照表現を検出する", () => {
  assert.equal(
    publish.isTruncatedAiReviewComment("# AI Review Result\n全文は別ファイルを参照"),
    true,
  );
});

test("publishAiReviewAndDispatch: 切り詰め本文は投稿を拒否する", async () => {
  await assert.rejects(
    () =>
      publish.publishAiReviewAndDispatch({
        repository: "o/r",
        prNumber: 10,
        commentBody: TRUNCATED_COMMENT,
        token: "t",
        fetchImpl: async () => {
          throw new Error("must not be called");
        },
      }),
    (error) => {
      assert.match(error.message, /truncated/i);
      return true;
    },
  );
});

function mockStatusSyncFetchImpl() {
  return async (url) => {
    if (String(url).includes("/actions/runs/99/jobs")) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          jobs: [{ name: "sync-project-status", status: "completed", conclusion: "success" }],
        }),
      };
    }
    throw new Error(`unexpected url: ${url}`);
  };
}

test("verifyAiReviewDispatch: 切り詰めコメントは truncated フラグを返す", async () => {
  const result = await publish.verifyAiReviewDispatch({
    repository: "o/r",
    prNumber: 10,
    token: "t",
    pollMaxWaitMs: 0,
    fetchImpl: mockStatusSyncFetchImpl(),
    listComments: async () => [
      {
        body: TRUNCATED_COMMENT,
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
  assert.equal(result.latest_ai_review_comment_truncated, true);
});

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
    pollMaxWaitMs: 0,
    fetchImpl: mockStatusSyncFetchImpl(),
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
    pollMaxWaitMs: 0,
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
    pollMaxWaitMs: 0,
    listComments: async () => [{ body: "hello", created_at: "2026-05-30T00:00:00Z" }],
    listRuns: async () => [],
  });
  assert.equal(result.ok, false);
  assert.equal(result.reason, "no_ai_review_comment");
});

test("verifyAiReviewDispatch: sinceIso より前のコメントは無視する", async () => {
  const result = await publish.verifyAiReviewDispatch({
    repository: "o/r",
    prNumber: 10,
    token: "t",
    pollMaxWaitMs: 0,
    sinceIso: "2026-05-30T12:00:00Z",
    listComments: async () => [
      {
        body: SAMPLE_COMMENT,
        created_at: "2026-05-30T00:00:00Z",
        html_url: "https://example.com/c/old",
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
  assert.equal(result.ok, false);
  assert.equal(result.reason, "no_ai_review_comment_since_run");
});

test("findLatestAiReviewComment: sinceIso 以降の最新を返す", () => {
  const comments = [
    {
      body: SAMPLE_COMMENT,
      created_at: "2026-05-30T00:00:00Z",
    },
    {
      body: SAMPLE_COMMENT.replace("approve_for_human_review", "request_changes"),
      created_at: "2026-05-30T13:00:00Z",
    },
  ];
  const latest = publish.findLatestAiReviewComment(comments, {
    sinceIso: "2026-05-30T12:00:00Z",
  });
  assert.equal(latest.created_at, "2026-05-30T13:00:00Z");
});

const REQUEST_CHANGES_WITH_NG = `# AI Review Result

## 1. レビュー結果

| 項目          | 内容                       |
| ------------- | -------------------------- |
| Review Result | \`request_changes\` |
| 対象PR        | \`#10\`                    |

## NG理由サマリ

- **テスト不足** / 対象: \`apps/api/foo.ts\` / 理由: 境界値テストがない

## 22. Status更新意図

| 次Status   | \`In Progress\` |
`;

const REQUEST_CHANGES_WITHOUT_NG = `# AI Review Result

## 1. レビュー結果

| 項目          | 内容                       |
| ------------- | -------------------------- |
| Review Result | \`request_changes\` |
| 対象PR        | \`#10\`                    |

## 22. Status更新意図

| 次Status   | \`In Progress\` |
`;

test("isMissingNgReasonSummary: request_changes でサマリ欠落を検出する", () => {
  assert.equal(publish.isMissingNgReasonSummary(REQUEST_CHANGES_WITHOUT_NG), true);
  assert.equal(publish.isMissingNgReasonSummary(REQUEST_CHANGES_WITH_NG), false);
  assert.equal(publish.isMissingNgReasonSummary(SAMPLE_COMMENT), false);
});

test("publishAiReviewAndDispatch: NG理由サマリ欠落は投稿を拒否する", async () => {
  await assert.rejects(
    () =>
      publish.publishAiReviewAndDispatch({
        repository: "o/r",
        prNumber: 10,
        commentBody: REQUEST_CHANGES_WITHOUT_NG,
        token: "t",
        fetchImpl: async () => {
          throw new Error("must not be called");
        },
      }),
    (error) => {
      assert.match(error.message, /NG理由サマリ/);
      return true;
    },
  );
});

test("verifyAiReviewDispatch: NG理由サマリ欠落フラグを返す", async () => {
  const result = await publish.verifyAiReviewDispatch({
    repository: "o/r",
    prNumber: 10,
    token: "t",
    pollMaxWaitMs: 0,
    fetchImpl: mockStatusSyncFetchImpl(),
    listComments: async () => [
      {
        body: REQUEST_CHANGES_WITHOUT_NG,
        created_at: "2026-05-30T00:00:00Z",
        html_url: "https://example.com/c/1",
      },
    ],
    listRuns: async () => [
      {
        id: 99,
        display_title: "status-sync · dispatch · PR #10 · request_changes",
        created_at: "2026-05-30T00:00:05Z",
        status: "completed",
        conclusion: "success",
        html_url: "https://example.com/run/99",
      },
    ],
  });
  assert.equal(result.ok, true);
  assert.equal(result.latest_ai_review_comment_missing_ng_summary, true);
});
