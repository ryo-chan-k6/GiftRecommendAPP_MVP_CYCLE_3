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

test("pickReviewDefinitionFromChangedFiles: PR diff から pr-review を選ぶ", () => {
  const path = resolver.pickReviewDefinitionFromChangedFiles(
    [
      { filename: "prompts/definitions/_e2e/review-fix-patterns-e2e/pr-review.yaml" },
      { filename: "prompts/definitions/_e2e/review-fix-patterns-e2e/task.yaml" },
    ],
    { summary: "review-fix-patterns-e2e" },
  );
  assert.equal(path, "prompts/definitions/_e2e/review-fix-patterns-e2e/pr-review.yaml");
});

test("resolveReviewDefinition: develop に無い場合は weak scan で not_found", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "resolve-review-"));
  write(
    path.join(root, "prompts/definitions/reviews/sample-a/pr-review.yaml"),
    'definition_type: "review"\n',
  );
  write(
    path.join(root, "prompts/definitions/reviews/sample-b/pr-review.yaml"),
    'definition_type: "review"\n',
  );

  const result = resolver.resolveReviewDefinition({
    workspaceRoot: root,
    headRef: "docs/task-289-review-fix-patterns-e2e",
    issueNumber: 289,
  });

  assert.equal(result.ok, false);
  assert.equal(result.reason, "review_definition_not_found");
});

test("extractTargetIssueNumber: target.issue の scalar 形式を解釈する", () => {
  const issue = resolver.extractTargetIssueNumber(
    'definition_type: "review"\ntarget:\n  pr: 315\n  issue: 314\n',
  );
  assert.equal(issue, 314);
});

test("extractTargetIssueNumber: target.issue.number の nested 形式を解釈する", () => {
  const issue = resolver.extractTargetIssueNumber(
    'definition_type: "review"\ntarget:\n  issue:\n    number: 300\n',
  );
  assert.equal(issue, 300);
});

test("resolveReviewDefinition: Epic Branch は epic/pr-review 慣例パスを優先する", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "resolve-review-epic-"));
  write(
    path.join(root, "prompts/definitions/reviews/contract-impl-task-separation/command-update/pr-review.yaml"),
    [
      'definition_type: "review"',
      "review:",
      '  type: "task_pr_review"',
      "target:",
      "  pr: 315",
      "  issue: 314",
      '  task_definition: "prompts/definitions/tasks/contract-impl-task-separation/command-update.yaml"',
    ].join("\n"),
  );
  write(
    path.join(root, "prompts/definitions/reviews/contract-impl-task-separation/contract-gate/pr-review.yaml"),
    [
      'definition_type: "review"',
      "review:",
      '  type: "task_pr_review"',
      "target:",
      "  pr: 312",
      "  issue: 311",
      '  task_definition: "prompts/definitions/tasks/contract-impl-task-separation/contract-gate.yaml"',
    ].join("\n"),
  );
  write(
    path.join(root, "prompts/definitions/reviews/contract-impl-task-separation/epic/pr-review.yaml"),
    [
      'definition_type: "review"',
      "review:",
      '  type: "epic_pr_review"',
      "target:",
      "  pr: 320",
      "  issue:",
      "    number: 300",
      '  task_definition: "prompts/definitions/epics/contract-impl-task-separation/epic.yaml"',
    ].join("\n"),
  );

  const result = resolver.resolveReviewDefinition({
    workspaceRoot: root,
    headRef: "refactor/epic-300-contract-impl-task-separation",
    issueNumber: 300,
    prNumber: 320,
    prBody: "Closes #300",
  });

  assert.equal(result.ok, true);
  assert.equal(
    result.path,
    "prompts/definitions/reviews/contract-impl-task-separation/epic/pr-review.yaml",
  );
  assert.equal(result.source, "epic_review_convention");
});

test("resolveReviewDefinition: Epic Branch で epic/pr-review が無い場合は task 定義を同点化しない", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "resolve-review-epic-"));
  write(
    path.join(root, "prompts/definitions/reviews/contract-impl-task-separation/command-update/pr-review.yaml"),
    [
      'definition_type: "review"',
      "review:",
      '  type: "task_pr_review"',
      "target:",
      "  pr: 315",
      "  issue: 314",
      '  task_definition: "prompts/definitions/tasks/contract-impl-task-separation/command-update.yaml"',
    ].join("\n"),
  );
  write(
    path.join(root, "prompts/definitions/reviews/contract-impl-task-separation/contract-gate/pr-review.yaml"),
    [
      'definition_type: "review"',
      "review:",
      '  type: "task_pr_review"',
      "target:",
      "  pr: 312",
      "  issue: 311",
      '  task_definition: "prompts/definitions/tasks/contract-impl-task-separation/contract-gate.yaml"',
    ].join("\n"),
  );
  write(
    path.join(root, "prompts/definitions/reviews/api-spec-deprecation-reference-update/pr-review.yaml"),
    [
      'definition_type: "review"',
      "review:",
      '  type: "task_pr_review"',
      "target:",
      "  pr: 310",
      "  issue: 309",
      '  task_definition: "prompts/definitions/tasks/contract-impl-task-separation/api-spec-deprecation-reference-update.yaml"',
    ].join("\n"),
  );

  const result = resolver.resolveReviewDefinition({
    workspaceRoot: root,
    headRef: "refactor/epic-300-contract-impl-task-separation",
    issueNumber: 300,
    prNumber: 320,
    prBody: "Closes #300",
  });

  assert.equal(result.ok, false);
  assert.notEqual(result.reason, "ambiguous_review_definition");
  assert.equal(result.reason, "review_definition_not_found");
  assert.match(result.hint || "", /epic\/pr-review\.yaml/);
});

test("resolveReviewDefinitionFromTaskPath: workstream review 慣例パスを解決する", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "resolve-review-"));
  const taskPath = "prompts/definitions/tasks/sample-workstream/my-task.yaml";
  const reviewPath = "prompts/definitions/reviews/sample-workstream/pr-review.yaml";
  write(path.join(root, taskPath), 'definition_type: "task"\n');
  write(
    path.join(root, reviewPath),
    `definition_type: "review"\ntarget:\n  task_definition: "${taskPath}"\n`,
  );

  const result = resolver.resolveReviewDefinitionFromTaskPath(taskPath, root);
  assert.equal(result.ok, true);
  assert.equal(result.path, reviewPath);
  assert.equal(result.source, "workstream_review_convention");
});

test("resolveReviewDefinition: Task Branch は target.issue / target.pr で一意解決する", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "resolve-review-task-"));
  write(
    path.join(root, "prompts/definitions/reviews/contract-impl-task-separation/command-update/pr-review.yaml"),
    [
      'definition_type: "review"',
      "review:",
      '  type: "task_pr_review"',
      "target:",
      "  pr: 315",
      "  issue: 314",
      '  task_definition: "prompts/definitions/tasks/contract-impl-task-separation/command-update.yaml"',
    ].join("\n"),
  );
  write(
    path.join(root, "prompts/definitions/reviews/contract-impl-task-separation/contract-gate/pr-review.yaml"),
    [
      'definition_type: "review"',
      "review:",
      '  type: "task_pr_review"',
      "target:",
      "  pr: 312",
      "  issue: 311",
      '  task_definition: "prompts/definitions/tasks/contract-impl-task-separation/contract-gate.yaml"',
    ].join("\n"),
  );

  const result = resolver.resolveReviewDefinition({
    workspaceRoot: root,
    headRef: "refactor/task-314-command-update",
    issueNumber: 314,
    prNumber: 315,
    prBody: "Related to #314",
  });

  assert.equal(result.ok, true);
  assert.equal(
    result.path,
    "prompts/definitions/reviews/contract-impl-task-separation/command-update/pr-review.yaml",
  );
  assert.equal(result.source, "scan");
});
