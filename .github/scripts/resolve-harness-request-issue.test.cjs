"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const requestIssue = require("./resolve-harness-request-issue.cjs");

test("resolveHarnessRequestIssue: pr-review.yaml の issue.number を優先", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "harness-issue-"));
  const reviewDir = path.join(dir, "prompts/definitions/reviews/demo");
  fs.mkdirSync(reviewDir, { recursive: true });
  fs.writeFileSync(
    path.join(reviewDir, "pr-review.yaml"),
    `target:
  issue:
    number: 368
`,
    "utf8",
  );
  const pull = {
    body: "Related to #366",
    head: { ref: "docs/task-368-demo-api-contract-spec" },
  };
  const resolved = requestIssue.resolveHarnessRequestIssue({
    workspaceRoot: dir,
    pull,
    issueNumberArg: "366",
    reviewDefinitionPath: "prompts/definitions/reviews/demo/pr-review.yaml",
  });
  assert.equal(resolved, 368);
  fs.rmSync(dir, { recursive: true, force: true });
});
