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

test("publishAiReviewHarnessFallback: result.json から transcript 不足を補完", async () => {
  const fs = require("node:fs");
  const os = require("node:os");
  const path = require("node:path");
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "harness-fallback-"));
  const resultPath = path.join(dir, "definition-run-result.json");
  fs.writeFileSync(
    resultPath,
    JSON.stringify({ status: "finished", result: SAMPLE_COMMENT }),
    "utf8",
  );

  const calls = [];
  const result = await fallback.publishAiReviewHarnessFallback({
    repository: "o/r",
    prNumber: 290,
    sinceIso: "2026-05-31T15:27:52Z",
    token: "bot-token",
    transcriptText: "",
    resultJsonPath: resultPath,
    fetchImpl: async (url, options) => {
      calls.push({ url, method: options && options.method });
      if (url.includes("/issues/290/comments") && (!options || !options.method || options.method === "GET")) {
        return { ok: true, json: async () => [] };
      }
      if (url.includes("/issues/290/comments") && options.method === "POST") {
        return {
          ok: true,
          status: 201,
          json: async () => ({ html_url: "https://example.com/c/3", id: 3 }),
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

  fs.rmSync(dir, { recursive: true, force: true });
  assert.equal(result.ok, true);
  assert.equal(result.reason, "published");
  assert.equal(calls.filter((c) => c.method === "POST").length, 2);
});

test("extractLatestAiReviewCommentFromTranscript: 切り詰めブロックは採用せず合成へ", () => {
  const truncated = `# AI Review Result

## 1. レビュー結果

| 項目          | 内容                       |
| ------------- | -------------------------- |
| Review Result | \`approve_for_human_review\` |
...

（全文は \`/tmp/ai-review-comment-302.md\` を参照）`;
  const body = fallback.extractLatestAiReviewCommentFromTranscript(truncated, { prNumber: 302 });
  assert.doesNotMatch(body, /\/tmp\//);
  assert.match(body, /harness-fallback: synthesized/);
  assert.match(body, /approve_for_human_review/);
});

test("extractLatestAiReviewCommentFromTranscript: 完全ブロックがあれば切り詰めより優先", () => {
  const truncated = `# AI Review Result

## 1. レビュー結果

| Review Result | \`request_changes\` |
...
（全文は \`/tmp/x.md\` を参照）`;
  const transcript = `${SAMPLE_COMMENT}\n---\n${truncated}`;
  const body = fallback.extractLatestAiReviewCommentFromTranscript(transcript);
  assert.doesNotMatch(body, /\/tmp\//);
  assert.match(body, /## 22\. Status更新意図/);
});

test("extractLatestAiReviewCommentFromTranscript: prose の単一トークンから合成", () => {
  const transcript = [
    "レビュー結論は approve_for_human_review です。",
    "Human Review へ進めて問題ありません。",
  ].join("\n");
  const body = fallback.extractLatestAiReviewCommentFromTranscript(transcript, { prNumber: 290 });
  assert.match(body, /# AI Review Result/);
  assert.match(body, /approve_for_human_review/);
  assert.match(body, /harness-fallback: synthesized/);
});

test("extractLatestAiReviewCommentFromTranscript: ## 1. レビュー結果 見出しから抽出", () => {
  const transcript = [
    "## 1. レビュー結果",
    "",
    "| 項目          | 内容                       |",
    "| Review Result | `request_changes` |",
    "",
    "## 22. Status更新意図",
    "| 次Status   | `In Progress` |",
  ].join("\n");
  const body = fallback.extractLatestAiReviewCommentFromTranscript(transcript);
  assert.match(body, /# AI Review Result/);
  assert.match(body, /request_changes/);
});

test("collectUniqueReviewResults: 複数トークンは合成しない", () => {
  const unique = fallback.collectUniqueReviewResults(
    "approve_for_human_review と request_changes が混在",
  );
  assert.equal(unique.length, 2);
});

test("publishAiReviewHarnessFallback: prose transcript から publish する", async () => {
  const calls = [];
  const result = await fallback.publishAiReviewHarnessFallback({
    repository: "o/r",
    prNumber: 290,
    sinceIso: "2026-05-31T15:27:52Z",
    token: "bot-token",
    transcriptText: "結論: approve_for_human_review。scope 内修正は完了。",
    fetchImpl: async (url, options) => {
      calls.push({ url, method: options && options.method });
      if (url.includes("/issues/290/comments") && (!options || !options.method || options.method === "GET")) {
        return { ok: true, json: async () => [] };
      }
      if (url.includes("/issues/290/comments") && options.method === "POST") {
        return {
          ok: true,
          status: 201,
          json: async () => ({ html_url: "https://example.com/c/4", id: 4 }),
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
  assert.equal(result.synthesized, true);
  assert.equal(calls.filter((c) => c.method === "POST").length, 2);
});

test("synthesizeAiReviewComment: request_changes で §7 から NG理由サマリを埋め込む", () => {
  const transcript = `
結論は request_changes です。

## 7. 修正必須事項

### 7.1 テスト不足

| 項目     | 内容                          |
| -------- | ----------------------------- |
| 重要度   | \`must\`           |
| 対象     | \`apps/api/foo.ts\`             |
| 分類     | \`test\`           |
| 対応方針 | 境界値テストを追加 |

#### 指摘内容

境界値がない。

#### 理由

acceptance_criteria を満たさない。
`;
  const body = fallback.synthesizeAiReviewComment({
    reviewResult: "request_changes",
    prNumber: 466,
    transcript,
  });
  assert.match(body, /## NG理由サマリ/);
  assert.match(body, /テスト不足/);
  assert.match(body, /apps\/api\/foo\.ts/);
  assert.match(body, /harness-fallback: synthesized/);
});

test("extractLatestAiReviewCommentFromTranscript: request_changes で指摘なし合成は NGサマリなし", () => {
  const body = fallback.extractLatestAiReviewCommentFromTranscript(
    "結論: request_changes。詳細は省略。",
    { prNumber: 466 },
  );
  assert.match(body, /request_changes/);
  assert.match(body, /## NG理由サマリ/);
  assert.match(body, /なし/);
});

test("publishAiReviewHarnessFallback: NG理由サマリ欠落は投稿しない", async () => {
  const result = await fallback.publishAiReviewHarnessFallback({
    repository: "o/r",
    prNumber: 466,
    sinceIso: "2026-05-31T15:27:52Z",
    token: "bot-token",
    transcriptText: "結論: request_changes。詳細なし。",
    fetchImpl: async (url, options) => {
      if (url.includes("/issues/466/comments") && (!options || !options.method || options.method === "GET")) {
        return { ok: true, json: async () => [] };
      }
      if (url.includes("/actions/workflows/pr-review-status-sync.yml/runs")) {
        return { ok: true, json: async () => ({ workflow_runs: [] }) };
      }
      if (options && options.method === "POST") {
        throw new Error("must not publish without NG summary");
      }
      throw new Error(url);
    },
  });
  assert.equal(result.ok, false);
  assert.equal(result.reason, "ng_reason_summary_missing");
});
