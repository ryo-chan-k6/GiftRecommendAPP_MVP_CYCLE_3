"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const slack = require("./slack-notify.cjs");

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
    token: "xoxb-test",
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
    token: "xoxb-test",
    channel: "C123",
    text: "hello",
    fetchImpl: async (url, options) => {
      assert.equal(url, "https://slack.com/api/chat.postMessage");
      assert.equal(options.headers.Authorization, "Bearer xoxb-test");
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

