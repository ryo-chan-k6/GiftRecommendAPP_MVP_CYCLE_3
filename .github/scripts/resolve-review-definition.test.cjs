"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const resolver = require("./resolve-review-definition.cjs");

function write(filePath, content) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, "utf8");
}

test("parseBranchRef: task branch を分解する", () => {
  assert.deepEqual(resolver.parseBranchRef("docs/task-289-review-fix-patterns-e2e"), {
    unit: "task",
    issueNumber: 289,
    summary: "review-fix-patterns-e2e",
  });
});

test("extractDefinitionPathsFromText: /review-pr @path を抽出する", () => {
  const paths = resolver.extractDefinitionPathsFromText(
    "next: /review-pr @prompts/definitions/_e2e/review-fix-patterns-e2e/pr-review.yaml #290",
  );
  assert.deepEqual(paths, ["prompts/definitions/_e2e/review-fix-patterns-e2e/pr-review.yaml"]);
});

test("resolveReviewDefinition: e2e branch summary から sibling pr-review を解決する", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "resolve-review-"));
  write(
    path.join(root, "prompts/definitions/_e2e/review-fix-patterns-e2e/task.yaml"),
    'definition_type: "task"\nreview:\n  ai_review_required: true\n',
  );
  write(
    path.join(root, "prompts/definitions/_e2e/review-fix-patterns-e2e/pr-review.yaml"),
    'definition_type: "review"\ntarget:\n  task_definition: "prompts/definitions/_e2e/review-fix-patterns-e2e/task.yaml"\n',
  );

  const result = resolver.resolveReviewDefinition({
    workspaceRoot: root,
    headRef: "docs/task-289-review-fix-patterns-e2e",
    issueNumber: 289,
  });

  assert.equal(result.ok, true);
  assert.equal(result.path, "prompts/definitions/_e2e/review-fix-patterns-e2e/pr-review.yaml");
  assert.equal(result.source, "e2e_branch_summary");
});

test("resolveAiReviewRequired: false のとき required=false", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "resolve-review-"));
  const taskPath = "prompts/definitions/tasks/sample/task.yaml";
  write(
    path.join(root, taskPath),
    'definition_type: "task"\nreview:\n  ai_review_required: false\n',
  );
  const reviewPath = "prompts/definitions/reviews/sample/pr-review.yaml";
  write(
    path.join(root, reviewPath),
    `definition_type: "review"\ntarget:\n  task_definition: "${taskPath}"\n`,
  );

  const gate = resolver.resolveAiReviewRequired({
    workspaceRoot: root,
    reviewDefinitionPath: reviewPath,
  });
  assert.equal(gate.required, false);
});
