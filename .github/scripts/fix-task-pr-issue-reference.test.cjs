"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fixer = require("./fix-task-pr-issue-reference.cjs");

test("normalizeTaskPrIssueReference: Closes を Related to に置換", () => {
  const body = "## 関連Issue\n\nCloses #451\n\n親 Epic: #435\n";
  const result = fixer.normalizeTaskPrIssueReference(body, 451);
  assert.equal(result.changed, true);
  assert.match(result.body, /Related to #451/);
  assert.doesNotMatch(result.body, /Closes #451/i);
});

test("normalizeTaskPrIssueReference: 既に Related to なら変更なし", () => {
  const body = "## 関連Issue\n\nRelated to #451\n";
  const result = fixer.normalizeTaskPrIssueReference(body, 451);
  assert.equal(result.changed, false);
  assert.equal(result.reason, "closes_not_found");
});

test("fixTaskPrIssueReference: Task Branch で PR 本文を更新", async () => {
  let patchedBody = null;
  const result = await fixer.fixTaskPrIssueReference({
    owner: "o",
    repo: "r",
    prNumber: 454,
    token: "token",
    fetchImpl: async (url, init) => {
      if (url.includes("/pulls/454") && init?.method === "PATCH") {
        patchedBody = JSON.parse(init.body).body;
        return { ok: true, status: 200, json: async () => ({}) };
      }
      if (url.includes("/pulls/454")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            body: "Closes #451",
            head: { ref: "docs/task-451-ranking-config-table-spec" },
          }),
        };
      }
      throw new Error(`unexpected url: ${url}`);
    },
  });

  assert.equal(result.ok, true);
  assert.equal(result.skipped, false);
  assert.equal(result.task_issue_number, 451);
  assert.match(patchedBody, /Related to #451/);
});
