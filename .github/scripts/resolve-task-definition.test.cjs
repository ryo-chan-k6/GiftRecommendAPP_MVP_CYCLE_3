"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const taskResolver = require("./resolve-task-definition.cjs");

function write(filePath, content) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, "utf8");
}

test("extractTaskDefinitionPathsFromText: tasks 配下の yaml のみ抽出", () => {
  const body = [
    "Definition: `prompts/definitions/tasks/fixer-auto-dispatch/fixer-dispatch-script.yaml`",
    "Review: `prompts/definitions/reviews/sample/pr-review.yaml`",
  ].join("\n");
  const paths = taskResolver.extractTaskDefinitionPathsFromText(body);
  assert.deepEqual(paths, ["prompts/definitions/tasks/fixer-auto-dispatch/fixer-dispatch-script.yaml"]);
});

test("pickTaskDefinitionFromChangedFiles: 単一 task yaml を返す", () => {
  const picked = taskResolver.pickTaskDefinitionFromChangedFiles(
    [{ filename: "prompts/definitions/tasks/fixer-auto-dispatch/fixer-dispatch-script.yaml" }],
    { unit: "task", issueNumber: 324, summary: "fixer-dispatch-script" },
  );
  assert.equal(picked, "prompts/definitions/tasks/fixer-auto-dispatch/fixer-dispatch-script.yaml");
});

test("resolveTaskDefinition: override で解決", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "task-def-"));
  const taskPath = "prompts/definitions/tasks/sample/task.yaml";
  write(path.join(root, taskPath), 'definition_type: "task"\n');

  const result = taskResolver.resolveTaskDefinition({
    workspaceRoot: root,
    definitionOverride: taskPath,
  });

  assert.equal(result.ok, true);
  assert.equal(result.source, "override");
});

test("resolveTaskDefinition: review yaml は override 不可", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "task-def-"));
  const reviewPath = "prompts/definitions/reviews/sample/pr-review.yaml";
  write(path.join(root, reviewPath), 'definition_type: "review"\n');

  const result = taskResolver.resolveTaskDefinition({
    workspaceRoot: root,
    definitionOverride: reviewPath,
  });

  assert.equal(result.ok, false);
  assert.equal(result.reason, "definition_override_not_task");
});

test("resolveTaskDefinition: Contract Definition を override で解決", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "task-def-"));
  const contractPath =
    "prompts/definitions/contracts/api-pub-003-item-detail/openapi-fragment.yaml";
  write(path.join(root, contractPath), 'definition_type: "contract"\n');

  const result = taskResolver.resolveTaskDefinition({
    workspaceRoot: root,
    definitionOverride: contractPath,
  });

  assert.equal(result.ok, true);
  assert.equal(result.path, contractPath);
  assert.equal(result.source, "override");
  assert.equal(result.definition_kind, "contract");
});

test("resolveTaskDefinition: PR #417 相当を review changed files から解決", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "task-def-"));
  const contractPath =
    "prompts/definitions/contracts/api-pub-003-item-detail/openapi-fragment.yaml";
  const reviewPath = "prompts/definitions/reviews/pub-003-item-detail-openapi/pr-review.yaml";
  write(path.join(root, contractPath), 'definition_type: "contract"\n');
  write(
    path.join(root, reviewPath),
    [
      'definition_type: "review"',
      "target:",
      `  task_definition: "${contractPath}"`,
      "  issue:",
      "    number: 416",
    ].join("\n"),
  );

  const prBody = [
    "| Definition | `prompts/definitions/contracts/api-pub-003-item-detail/openapi-fragment.yaml` |",
    "## Review Definition",
    "`prompts/definitions/reviews/pub-003-item-detail-openapi/pr-review.yaml`",
    "Related to #416",
  ].join("\n");

  const result = taskResolver.resolveTaskDefinition({
    workspaceRoot: root,
    prBody,
    issueBody: "",
    headRef: "feature/task-416-pub-003-item-detail-openapi",
    issueNumber: 416,
    changedFiles: [
      { filename: "packages/contracts/openapi/public-api.yaml" },
      { filename: contractPath },
      { filename: reviewPath },
    ],
  });

  assert.equal(result.ok, true);
  assert.equal(result.path, contractPath);
  assert.equal(result.definition_kind, "contract");
  assert.match(result.source, /contract|review/);
});
