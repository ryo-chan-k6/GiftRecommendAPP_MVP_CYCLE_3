"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const slack = require("./slack-notify.cjs");

const DUMMY_SLACK_TOKEN = ["xox", "b-", "test"].join("");

test("buildSlackText: level title fields linksを整形する", () => {
  const text = slack.buildSlackText({
    level: "review",
    title: "Human Reviewをお願いします",
    summary: "AI Reviewが完了しました。",
    fields: { PR: "#12", Status: "Human Review" },
    links: { PR: "https://example.test/pull/12" },
    humanAction: "PRを確認してください。",
    mention: "<@U123>",
  });
  assert.match(text, /<@U123>/);
  assert.match(text, /\*\[review\] Human Reviewをお願いします\*/);
  assert.match(text, /- PR: #12/);
  assert.match(text, /PRを確認してください。/);
});

test("thread marker: build and extract", () => {
  const marker = slack.buildThreadMarker({
    threadKey: "pr:owner/repo#10",
    channel: "C123",
    ts: "1710000000.000100",
  });
  const markers = slack.extractThreadMarkers(`${marker}\nbody`);
  assert.equal(markers.length, 1);
  assert.equal(markers[0].key, "pr:owner/repo#10");
  assert.equal(markers[0].channel, "C123");
  assert.equal(markers[0].ts, "1710000000.000100");
});

test("findThreadTsFromComments: 最新コメントのmarkerを返す", () => {
  const comments = [
    { body: slack.buildThreadMarker({ threadKey: "issue:o/r#1", channel: "C1", ts: "1.000" }) },
    { body: slack.buildThreadMarker({ threadKey: "issue:o/r#1", channel: "C1", ts: "2.000" }) },
  ];
  assert.equal(slack.findThreadTsFromComments(comments, "issue:o/r#1", "C1"), "2.000");
});

test("postSlackMessage: dry_runではAPIを呼ばない", async () => {
  let called = false;
  const result = await slack.postSlackMessage({
    token: DUMMY_SLACK_TOKEN,
    channel: "C123",
    text: "hello",
    dryRun: true,
    fetchImpl: async () => {
      called = true;
    },
  });
  assert.equal(result.ok, true);
  assert.equal(result.dryRun, true);
  assert.equal(called, false);
});

test("postSlackMessage: 設定不足はskip扱い", async () => {
  const result = await slack.postSlackMessage({
    token: "",
    channel: "C123",
    text: "hello",
  });
  assert.equal(result.ok, false);
  assert.equal(result.skipped, true);
  assert.equal(result.error, "missing_slack_config");
});

test("postSlackMessage: Slack APIのokレスポンスを返す", async () => {
  const result = await slack.postSlackMessage({
    token: DUMMY_SLACK_TOKEN,
    channel: "C123",
    text: "hello",
    fetchImpl: async (url, options) => {
      assert.equal(url, "https://slack.com/api/chat.postMessage");
      assert.equal(options.headers.Authorization, `Bearer ${DUMMY_SLACK_TOKEN}`);
      return {
        status: 200,
        async json() {
          return { ok: true, channel: "C123", ts: "1710000000.000100" };
        },
      };
    },
  });
  assert.equal(result.ok, true);
  assert.equal(result.ts, "1710000000.000100");
});

test("relatedIssueNumber: Related toを優先する", () => {
  assert.equal(slack.relatedIssueNumber("Related to #123\nCloses #999"), 123);
  assert.equal(slack.relatedIssueNumber("Closes #45"), 45);
  assert.equal(slack.relatedIssueNumber("no issue"), 0);
});

test("Review Result: 英語と日本語を正規化する", () => {
  assert.equal(slack.normalizeReviewResult("Review Result | `approve_for_human_review`"), "approve_for_human_review");
  assert.equal(slack.normalizeReviewResult("Human Reviewへ進行可"), "approve_for_human_review");
  assert.equal(slack.statusFromReviewResult("needs_human_decision", ""), "Human Review");
  assert.equal(slack.statusFromReviewResult("needs_human_decision", "| 次Status | `In Progress` |"), "In Progress");
  assert.equal(slack.notificationLevelFromReviewResult("blocked"), "error");
});

const SAMPLE_AI_REVIEW = `# AI Review Result

## 1. レビュー結果

| 項目          | 内容                     |
| ------------- | ------------------------ |
| Review Result | \`approve_for_human_review\` |
| 対象PR        | \`268\`                  |

### Review Result の分類

| 分類                       | 意味 |
| approve_for_human_review | Human Review |

## 22. Status更新意図

| 次Status   | \`Human Review\` |
`;

test("isAutomationBypassComment: Status同期・Slack markerを除外する", () => {
  assert.equal(
    slack.isAutomationBypassComment(
      "Project Status更新意図: Issue #265 を `Human Review` へ更新しました（Review Result: `approve_for_human_review`）。",
    ),
    true,
  );
  assert.equal(slack.isAutomationBypassComment(slack.buildThreadMarkerCommentBody({
    threadKey: "pr:o/r#1",
    channel: "C1",
    ts: "1.000",
  })), true);
  assert.equal(slack.isAutomationBypassComment(SAMPLE_AI_REVIEW), false);
});

test("isAiReviewResultComment: AI Reviewテンプレのみtrue", () => {
  assert.equal(slack.isAiReviewResultComment(SAMPLE_AI_REVIEW), true);
  assert.equal(
    slack.isAiReviewResultComment("Project Status更新意図: Issue #1 を `Human Review` へ更新しました。"),
    false,
  );
  assert.equal(slack.isAiReviewResultComment("random approve_for_human_review mention"), false);
});

test("extractReviewResultFromAiComment: §1表から一意に抽出する", () => {
  const extracted = slack.extractReviewResultFromAiComment(SAMPLE_AI_REVIEW);
  assert.equal(extracted.ok, true);
  assert.equal(extracted.value, "approve_for_human_review");
});

test("extractReviewResultFromAiComment: 運用確認コメントは対象外", () => {
  const extracted = slack.extractReviewResultFromAiComment(
    "Project Status更新意図: Issue #265 を `Human Review` へ更新しました（Review Result: approve_for_human_review）。",
  );
  assert.equal(extracted.ok, false);
  assert.equal(extracted.reason, "not_ai_review_comment");
});

test("buildStatusSyncConfirmationComment: Review Result enumを含めない", () => {
  const body = slack.buildStatusSyncConfirmationComment({ taskIssueNumber: 265, nextStatus: "Human Review" });
  assert.match(body, /^Project Status更新意図:/);
  assert.equal(body.includes("approve_for_human_review"), false);
  assert.equal(slack.isAutomationBypassComment(body), true);
});

test("statusNamesEqual: 大文字小文字を無視する", () => {
  assert.equal(slack.statusNamesEqual("AI Review", "ai review"), true);
  assert.equal(slack.statusNamesEqual("Human Review", "In Progress"), false);
});

test("expectedCurrentStatusForAiReview: AI Review前提", () => {
  assert.equal(slack.expectedCurrentStatusForAiReview("approve_for_human_review"), "AI Review");
});

test("ループ再現: AI Review1回+確認コメントは追加トリガにならない", () => {
  const ai = SAMPLE_AI_REVIEW;
  const confirm = slack.buildStatusSyncConfirmationComment({
    taskIssueNumber: 265,
    nextStatus: "Human Review",
  });
  assert.equal(slack.isAiReviewResultComment(ai), true);
  assert.equal(slack.isAiReviewResultComment(confirm), false);
  assert.equal(slack.isAutomationBypassComment(confirm), true);
  assert.equal(slack.extractReviewResultFromAiComment(confirm).ok, false);
});

test("upsertThreadMarkerComment: 既存markerがあれば更新する", async () => {
  const calls = [];
  const github = {
    rest: {
      issues: {
        async updateComment(args) {
          calls.push(["update", args]);
        },
        async createComment(args) {
          calls.push(["create", args]);
          return { data: { id: 2 } };
        },
      },
    },
  };
  const comments = [
    {
      id: 1,
      body: slack.buildThreadMarker({ threadKey: "pr:o/r#1", channel: "C1", ts: "1.000" }),
    },
  ];
  const result = await slack.upsertThreadMarkerComment({
    github,
    owner: "o",
    repo: "r",
    issueNumber: 1,
    threadKey: "pr:o/r#1",
    channel: "C1",
    ts: "2.000",
    comments,
  });
  assert.equal(result.ok, true);
  assert.equal(result.action, "update");
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "update");
  assert.match(calls[0][1].body, /ts=2.000/);
});

const SAMPLE_FIX_COMPLETE = `# Fix Review Comments Result

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

test("isFixCompleteResultComment: fix-complete形式を識別する", () => {
  assert.equal(slack.isFixCompleteResultComment(SAMPLE_FIX_COMPLETE), true);
  assert.equal(slack.extractFixOutcomeFromComment(SAMPLE_FIX_COMPLETE).value, "ready_for_ai_review");
});

test("extractFixOutcomeFromComment: split_requiredはdispatch対象外", () => {
  const body = SAMPLE_FIX_COMPLETE.replace("ready_for_ai_review", "split_required");
  assert.equal(slack.extractFixOutcomeFromComment(body).value, "split_required");
});

test("expectedCurrentStatusForFixComplete: In Progressを前提とする", () => {
  assert.equal(slack.expectedCurrentStatusForFixComplete(), "In Progress");
});

