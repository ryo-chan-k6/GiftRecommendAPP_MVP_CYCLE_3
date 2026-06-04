"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const post = require("./definition-run-post-verify.cjs");

function buildIssue({ number, title = "", login = "user", created_at, is_pr = false }) {
  return {
    number,
    title,
    html_url: `https://example.test/issues/${number}`,
    created_at,
    user: { login },
    pull_request: is_pr ? { url: `https://example.test/pull/${number}` } : undefined,
  };
}

function buildPull({ number, title = "", login = "user", created_at }) {
  return {
    number,
    title,
    html_url: `https://example.test/pull/${number}`,
    created_at,
    user: { login },
  };
}

function buildBranch({ name, login = "user", committed_at, sha = "abcdef0" }) {
  return { name, sha, author_login: login, committer_login: login, committed_at };
}

test("actorIsAutomation: 既定の bot を識別する", () => {
  assert.equal(post.actorIsAutomation("github-actions[bot]"), true);
  assert.equal(post.actorIsAutomation("github-actions"), true);
  assert.equal(post.actorIsAutomation(""), false);
  assert.equal(post.actorIsAutomation("random-user"), false);
});

test("classifyActor: automation / definition-run / unknown を分類", () => {
  assert.equal(
    post.classifyActor({ login: "github-actions[bot]", runActor: "octocat" }),
    "automation",
  );
  assert.equal(
    post.classifyActor({ login: "octocat", runActor: "octocat" }),
    "definition-run",
  );
  assert.equal(
    post.classifyActor({ login: "external-user", runActor: "octocat" }),
    "definition-run",
  );
  assert.equal(post.classifyActor({ login: "", runActor: "octocat" }), "unknown");
});

test("formatViolationsMarkdown: 違反 0 件は None 表示", () => {
  const md = post.formatViolationsMarkdown({
    started_at: "2026-01-01T00:00:00.000Z",
    run_mode: "dry-run",
    counts: { issues: 0, pull_requests: 0, branches: 0, violations: 0 },
    candidates: [],
    violations: [],
  });
  assert.match(md, /### Guard Violations \(post-run\)/);
  assert.match(md, /result: None/);
});

test("formatViolationsMarkdown: 違反ありは表形式で列挙", () => {
  const md = post.formatViolationsMarkdown({
    started_at: "2026-01-01T00:00:00.000Z",
    run_mode: "dry-run",
    counts: { issues: 1, pull_requests: 0, branches: 0, violations: 1 },
    candidates: [],
    violations: [
      {
        type: "issue",
        number: 99,
        title: "rogue issue",
        url: "https://example.test/issues/99",
        created_at: "2026-01-01T00:05:00.000Z",
        actor_login: "octocat",
        actor_type: "definition-run",
      },
    ],
  });
  assert.match(md, /\| type \| identifier \|/);
  assert.match(md, /\| issue \| #99 rogue issue \| octocat \(definition-run\)/);
});

test("runPostVerify dry-run: started_at 以降の新規 Issue / PR / Branch を全件違反扱い", async () => {
  const startedAt = "2026-01-01T00:00:00.000Z";
  const since = (item, key) => post.parseDate(item[key]) >= post.parseDate(startedAt);
  const result = await post.runPostVerify({
    octokit: {},
    owner: "owner",
    repo: "repo",
    startedAt,
    runMode: "dry-run",
    runActor: "octocat",
    listIssues: async () =>
      [
        buildIssue({ number: 10, title: "new issue", login: "octocat", created_at: "2026-01-01T00:01:00.000Z" }),
        buildIssue({ number: 11, title: "old issue", login: "octocat", created_at: "2025-12-31T23:00:00.000Z" }),
      ].filter((item) => since(item, "created_at")),
    listPulls: async () =>
      [
        buildPull({ number: 20, title: "pr", login: "octocat", created_at: "2026-01-01T00:02:00.000Z" }),
      ].filter((item) => since(item, "created_at")),
    listBranches: async () =>
      [
        buildBranch({ name: "feature/new", login: "octocat", committed_at: "2026-01-01T00:03:00.000Z" }),
      ].filter((item) => since(item, "committed_at")),
  });
  assert.equal(result.run_mode, "dry-run");
  assert.equal(result.counts.violations, 3);
  const kinds = result.violations.map((v) => v.type).sort();
  assert.deepEqual(kinds, ["branch", "issue", "pull_request"]);
});

test("runPostVerify dry-run: automation 由来 (github-actions[bot]) も違反扱い", async () => {
  const result = await post.runPostVerify({
    octokit: {},
    owner: "o",
    repo: "r",
    startedAt: "2026-01-01T00:00:00.000Z",
    runMode: "dry-run",
    runActor: "octocat",
    listIssues: async () => [
      buildIssue({
        number: 30,
        title: "by bot",
        login: "github-actions[bot]",
        created_at: "2026-01-01T01:00:00.000Z",
      }),
    ],
    listPulls: async () => [],
    listBranches: async () => [],
  });
  assert.equal(result.counts.violations, 1);
  assert.equal(result.violations[0].actor_type, "automation");
});

test("runPostVerify dry-run: 違反 0 件は OK", async () => {
  const result = await post.runPostVerify({
    octokit: {},
    owner: "o",
    repo: "r",
    startedAt: "2026-01-01T00:00:00.000Z",
    runMode: "dry-run",
    runActor: "octocat",
    listIssues: async () => [],
    listPulls: async () => [],
    listBranches: async () => [],
  });
  assert.equal(result.counts.violations, 0);
  assert.deepEqual(result.violations, []);
});

test("runPostVerify live-run (将来): automation は許容、Cloud Agent の PR / Branch は違反", async () => {
  const result = await post.runPostVerify({
    octokit: {},
    owner: "o",
    repo: "r",
    startedAt: "2026-01-01T00:00:00.000Z",
    runMode: "live-run",
    runActor: "octocat",
    listIssues: async () => [
      buildIssue({ number: 1, title: "issue by agent", login: "octocat", created_at: "2026-01-01T00:01:00.000Z" }),
    ],
    listPulls: async () => [
      buildPull({ number: 2, title: "pr by agent", login: "octocat", created_at: "2026-01-01T00:02:00.000Z" }),
      buildPull({ number: 3, title: "pr by bot", login: "github-actions[bot]", created_at: "2026-01-01T00:03:00.000Z" }),
    ],
    listBranches: async () => [
      buildBranch({ name: "feature/agent", login: "octocat", committed_at: "2026-01-01T00:04:00.000Z" }),
      buildBranch({ name: "feature/bot", login: "github-actions[bot]", committed_at: "2026-01-01T00:05:00.000Z" }),
    ],
  });
  assert.equal(result.counts.violations, 2);
  const ids = result.violations.map((v) => `${v.type}:${v.actor_type}`).sort();
  assert.deepEqual(ids, ["branch:definition-run", "pull_request:definition-run"]);
});

test("runPostVerify: startedAt 未指定はエラー", async () => {
  await assert.rejects(
    () =>
      post.runPostVerify({
        owner: "o",
        repo: "r",
        runMode: "dry-run",
      }),
    /startedAt is required/,
  );
});

test("runPostVerify: owner / repo 未指定はエラー", async () => {
  await assert.rejects(
    () =>
      post.runPostVerify({
        startedAt: "2026-01-01T00:00:00.000Z",
        runMode: "dry-run",
      }),
    /owner \/ repo are required/,
  );
});

test("listIssuesCreatedSince: octokit 経由で PR 以外の Issue のみ返す", async () => {
  const startedAt = "2026-01-01T00:00:00.000Z";
  const called = [];
  const octokit = {
    rest: {
      issues: {
        listForRepo: async (params) => {
          called.push(params);
          return {
            data: [
              buildIssue({ number: 1, title: "issue", login: "u", created_at: "2026-01-01T00:01:00Z" }),
              buildIssue({ number: 2, title: "pr-like", login: "u", created_at: "2026-01-01T00:02:00Z", is_pr: true }),
            ],
          };
        },
      },
    },
  };
  const result = await post.listIssuesCreatedSince({ octokit, owner: "o", repo: "r", since: startedAt });
  assert.equal(result.length, 1);
  assert.equal(result[0].number, 1);
  assert.equal(called[0].owner, "o");
  assert.equal(called[0].since, "2026-01-01T00:00:00.000Z");
});

test("runPostVerify: review-pr live-run で dispatch 欠落は violation", async () => {
  const result = await post.runPostVerify({
    owner: "o",
    repo: "r",
    startedAt: "2026-01-01T00:00:00.000Z",
    runMode: "live-run",
    runActor: "agent",
    command: "review-pr",
    targetPr: "282",
    token: "t",
    listIssues: async () => [],
    listPulls: async () => [],
    listBranches: async () => [],
    verifyImpl: async () => ({
      ok: false,
      reason: "dispatch_missing",
      message: "missing",
      recovery_command: "node ... --dispatch-only",
    }),
  });
  assert.equal(result.counts.violations, 1);
  assert.equal(result.violations[0].type, "review_dispatch");
  assert.equal(result.dispatch_verify.ok, false);
});

test("runPostVerify: review-pr live-run で dispatch 済みなら violation なし", async () => {
  const result = await post.runPostVerify({
    owner: "o",
    repo: "r",
    startedAt: "2026-01-01T00:00:00.000Z",
    runMode: "live-run",
    runActor: "agent",
    command: "review-pr",
    targetPr: "282",
    token: "t",
    listIssues: async () => [],
    listPulls: async () => [],
    listBranches: async () => [],
    verifyImpl: async () => ({
      ok: true,
      dispatch_run_id: 1,
    }),
  });
  assert.equal(result.counts.violations, 0);
  assert.equal(result.dispatch_verify.ok, true);
});

test("runPostVerify: review-pr live-run で投稿済みコメントが切り詰めなら violation", async () => {
  const result = await post.runPostVerify({
    owner: "o",
    repo: "r",
    startedAt: "2026-01-01T00:00:00.000Z",
    runMode: "live-run",
    runActor: "agent",
    command: "review-pr",
    targetPr: "282",
    token: "t",
    listIssues: async () => [],
    listPulls: async () => [],
    listBranches: async () => [],
    verifyImpl: async () => ({
      ok: true,
      dispatch_run_id: 1,
      latest_ai_review_comment_truncated: true,
      latest_ai_review_comment_url: "https://example.com/c/1",
    }),
  });
  assert.equal(result.counts.violations, 1);
  assert.equal(result.violations[0].type, "review_comment_truncated");
});

test("runPostVerify: review-pr live-run は対象 PR head branch の commit 更新を違反にしない", async () => {
  const result = await post.runPostVerify({
    octokit: {},
    owner: "o",
    repo: "r",
    startedAt: "2026-01-01T00:00:00.000Z",
    runMode: "live-run",
    runActor: "agent",
    command: "review-pr",
    targetPr: "290",
    token: "t",
    getPullImpl: async () => ({ head: { ref: "docs/task-289-review-fix-patterns-e2e" } }),
    listIssues: async () => [],
    listPulls: async () => [],
    listBranches: async () => [
      buildBranch({
        name: "docs/task-289-review-fix-patterns-e2e",
        login: "okuri-ai-bot",
        committed_at: "2026-01-01T00:04:00.000Z",
      }),
      buildBranch({
        name: "feature/unrelated",
        login: "agent",
        committed_at: "2026-01-01T00:05:00.000Z",
      }),
    ],
    verifyImpl: async () => ({ ok: true, dispatch_run_id: 1 }),
  });
  assert.equal(result.excluded_pr_head_ref, "docs/task-289-review-fix-patterns-e2e");
  assert.equal(result.counts.branches, 1);
  assert.equal(result.counts.violations, 1);
  assert.equal(result.violations[0].type, "branch");
  assert.equal(result.violations[0].name, "feature/unrelated");
});

test("runPostVerify: fix-review-comments live-run は対象 PR head branch の commit 更新を違反にしない", async () => {
  const result = await post.runPostVerify({
    octokit: {},
    owner: "o",
    repo: "r",
    startedAt: "2026-01-01T00:00:00.000Z",
    runMode: "live-run",
    runActor: "agent",
    command: "fix-review-comments",
    targetPr: "359",
    token: "t",
    getPullImpl: async () => ({
      head: { ref: "docs/task-358-api-pub-002-recommendation-run-api-spec" },
    }),
    listIssues: async () => [],
    listPulls: async () => [],
    listBranches: async () => [
      buildBranch({
        name: "docs/task-358-api-pub-002-recommendation-run-api-spec",
        login: "okuri-ai-bot",
        committed_at: "2026-01-01T00:04:00.000Z",
      }),
      buildBranch({
        name: "feature/unrelated",
        login: "agent",
        committed_at: "2026-01-01T00:05:00.000Z",
      }),
    ],
  });
  assert.equal(result.excluded_pr_head_ref, "docs/task-358-api-pub-002-recommendation-run-api-spec");
  assert.equal(result.counts.branches, 1);
  assert.equal(result.counts.violations, 1);
  assert.equal(result.violations[0].type, "branch");
  assert.equal(result.violations[0].name, "feature/unrelated");
});
