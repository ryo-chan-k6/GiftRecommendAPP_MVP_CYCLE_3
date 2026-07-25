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

test("extractLatestAiReviewCommentFromTranscript: テンプレート水平線を含んでも全文抽出する", () => {
  const transcript = `# AI Review Result

## 1. レビュー結果

| 項目          | 内容                     |
| ------------- | ------------------------ |
| Review Result | \`request_changes\` |
| 対象PR        | \`#1626\`                  |

### Review Result の分類

| 分類                       | 意味 |
| -------------------------- | ---- |
| \`request_changes\`          | 修正 |

---

## NG理由サマリ

- **抽出打ち切り** / 対象: \`TRANSCRIPT_STOP\` / 理由: 水平線で途切れていた

---

## 2. 結論

テンプレート準拠全文が投稿できること。

## 7. 修正必須事項

### 7.1 抽出打ち切り

| 項目     | 内容                          |
| -------- | ----------------------------- |
| 重要度   | \`must\`           |
| 対象     | \`publish-ai-review-harness-fallback.cjs\` |
| 分類     | \`source\`           |
| 対応方針 | 水平線で終端しない |

#### 指摘内容

水平線で途切れる。

#### 理由

acceptance_criteria を満たさない。

## 22. Status更新意図

| 次Status   | \`In Progress\` |
`;
  const body = fallback.extractLatestAiReviewCommentFromTranscript(transcript, { prNumber: 1626 });
  assert.doesNotMatch(body, /harness-fallback: synthesized/);
  assert.match(body, /## NG理由サマリ/);
  assert.match(body, /抽出打ち切り/);
  assert.match(body, /## 7\. 修正必須事項/);
  assert.match(body, /### 7\.1 抽出打ち切り/);
  assert.match(body, /## 22\. Status更新意図/);
});

test("extractLatestAiReviewCommentFromTranscript: 不完全抽出時は §7 から synthesize する", () => {
  // 意図的に §1 のみの不完全ブロック + transcript 後方に §7 があるケースを模擬する。
  // （旧実装は usable な不完全ブロックを優先し synthesize に到達しなかった）
  const incomplete = `# AI Review Result

## 1. レビュー結果

| Review Result | \`request_changes\` |
| 対象PR        | \`#1626\` |
`;
  const rest = `
（中略・ログ）

## 7. 修正必須事項

### 7.1 フォールバック未到達

| 項目     | 内容                          |
| -------- | ----------------------------- |
| 重要度   | \`must\`           |
| 対象     | \`fallback synthesize\` |
| 分類     | \`source\`           |
| 対応方針 | 欠落時に synthesize |

#### 理由

不完全抽出だけでは NGサマリが埋まらない。
`;
  const body = fallback.extractLatestAiReviewCommentFromTranscript(`${incomplete}\n${rest}`, {
    prNumber: 1626,
  });
  assert.match(body, /harness-fallback: synthesized/);
  assert.match(body, /## NG理由サマリ/);
  assert.match(body, /フォールバック未到達/);
  assert.match(body, /fallback synthesize/);
});

test("publishAiReviewHarnessFallback: 水平線付き全文は投稿する", async () => {
  const transcript = `# AI Review Result

## 1. レビュー結果

| Review Result | \`request_changes\` |
| 対象PR        | \`#466\` |

---

## NG理由サマリ

- **水平線耐性** / 対象: \`extract\` / 理由: 全文が残る

---

## 2. 結論

ok

## 7. 修正必須事項

### 7.1 水平線耐性

| 重要度 | \`must\` |
| 対象 | \`extract\` |

#### 理由

回帰防止

## 22. Status更新意図

| 次Status | \`In Progress\` |
`;
  const posted = [];
  const result = await fallback.publishAiReviewHarnessFallback({
    repository: "o/r",
    prNumber: 466,
    sinceIso: "2026-05-31T15:27:52Z",
    token: "bot-token",
    transcriptText: transcript,
    fetchImpl: async (url, options) => {
      if (url.includes("/issues/466/comments") && (!options || !options.method || options.method === "GET")) {
        return { ok: true, json: async () => [] };
      }
      if (url.includes("/issues/466/comments") && options.method === "POST") {
        posted.push(JSON.parse(options.body).body);
        return {
          ok: true,
          status: 201,
          json: async () => ({ html_url: "https://example.com/c/5", id: 5 }),
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
  assert.equal(result.synthesized, false);
  assert.match(posted[0], /## NG理由サマリ/);
  assert.match(posted[0], /水平線耐性/);
  assert.match(posted[0], /### 7\.1/);
});
