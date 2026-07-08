"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const harness = require("./dispatch-definition-run.cjs");
const auto = require("./dispatch-review-pr-harness.cjs");

function write(filePath, content) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, "utf8");
}

function jsonResponse(data) {
  return {
    ok: true,
    status: 200,
    json: async () => data,
    text: async () => JSON.stringify(data),
  };
}

test("buildClientPayload: review-pr live-run payload", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "dispatch-run-"));
  const definition = "prompts/definitions/_examples/review-definition.example.yaml";
  write(path.join(root, definition), 'definition_type: "review"\n');
  const payload = harness.buildClientPayload({
    command: "review-pr",
    definition,
    runMode: "live-run",
    targetPr: "290",
    requestIssue: "289",
    requestedBy: "pr-created-status-sync",
    workspaceRoot: root,
  });
  assert.equal(payload.command, "review-pr");
  assert.equal(payload.run_mode, "live-run");
  assert.equal(payload.target_pr, "290");
  assert.equal(payload.request_issue, "289");
});

test("dispatchDefinitionRun: dry_run では API を呼ばない", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "dispatch-run-"));
  const definition = "prompts/definitions/_examples/review-definition.example.yaml";
  write(path.join(root, definition), 'definition_type: "review"\n');
  let called = false;
  const result = await harness.dispatchDefinitionRun({
    owner: "o",
    repo: "r",
    definition,
    targetPr: "1",
    workspaceRoot: root,
    token: "token",
    dryRun: true,
    fetchImpl: async () => {
      called = true;
    },
  });
  assert.equal(result.ok, true);
  assert.equal(called, false);
});

test("dispatchReviewPrHarness: ai_review_not_required は skipped", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "dispatch-auto-"));
  const taskPath = "prompts/definitions/_e2e/sample/task.yaml";
  const reviewPath = "prompts/definitions/_e2e/sample/pr-review.yaml";
  write(path.join(root, taskPath), 'definition_type: "task"\nreview:\n  ai_review_required: false\n');
  write(
    path.join(root, reviewPath),
    `definition_type: "review"\ntarget:\n  task_definition: "${taskPath}"\n`,
  );

  const result = await auto.dispatchReviewPrHarness({
    owner: "o",
    repo: "r",
    prNumber: 10,
    issueNumber: 9,
    definition: reviewPath,
    workspaceRoot: root,
    token: "token",
    fetchImpl: async (url) => {
      if (url.includes("/pulls/10")) {
        return jsonResponse({
          body: "Related to #9",
          head: { ref: "docs/task-9-sample", repo: { full_name: "o/r" } },
        });
      }
      if (url.includes("/issues/9")) {
        return jsonResponse({ body: "" });
      }
      throw new Error(`unexpected url: ${url}`);
    },
  });

  assert.equal(result.ok, true);
  assert.equal(result.skipped, true);
  assert.equal(result.reason, "ai_review_not_required");
});

test("dispatchReviewPrHarness: 解決成功時に definition-run を dispatch", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "dispatch-auto-"));
  const taskPath = "prompts/definitions/_e2e/sample/task.yaml";
  const reviewPath = "prompts/definitions/_e2e/sample/pr-review.yaml";
  write(path.join(root, taskPath), 'definition_type: "task"\nreview:\n  ai_review_required: true\n');
  write(
    path.join(root, reviewPath),
    `definition_type: "review"\ntarget:\n  task_definition: "${taskPath}"\n`,
  );

  let dispatchBody = null;
  const result = await auto.dispatchReviewPrHarness({
    owner: "o",
    repo: "r",
    prNumber: 10,
    issueNumber: 9,
    definition: reviewPath,
    requestedBy: "test",
    workspaceRoot: root,
    token: "token",
    fetchImpl: async (url, init) => {
      if (url.includes("/pulls/10")) {
        return jsonResponse({
          body: "Related to #9",
          head: { ref: "docs/task-9-sample", repo: { full_name: "o/r" } },
        });
      }
      if (url.includes("/issues/9")) {
        return jsonResponse({ body: "" });
      }
      if (url.endsWith("/dispatches") && init?.method === "POST") {
        dispatchBody = JSON.parse(init.body);
        return { ok: true, status: 204, text: async () => "" };
      }
      throw new Error(`unexpected url: ${url}`);
    },
  });

  assert.equal(result.ok, true);
  assert.equal(dispatchBody.event_type, "definition-run");
  assert.equal(dispatchBody.client_payload.command, "review-pr");
  assert.equal(dispatchBody.client_payload.definition, reviewPath);
  assert.equal(dispatchBody.client_payload.target_pr, "10");
  assert.equal(dispatchBody.client_payload.ref, "docs/task-9-sample");
});

test("dispatchReviewPrHarness: local 解決失敗時 PR files から fallback", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "dispatch-auto-"));
  write(
    path.join(root, "prompts/definitions/reviews/sample-a/pr-review.yaml"),
    'definition_type: "review"\n',
  );
  write(
    path.join(root, "prompts/definitions/reviews/sample-b/pr-review.yaml"),
    'definition_type: "review"\n',
  );

  let dispatchBody = null;
  const result = await auto.dispatchReviewPrHarness({
    owner: "o",
    repo: "r",
    prNumber: 290,
    issueNumber: 289,
    requestedBy: "test",
    workspaceRoot: root,
    token: "token",
    fetchImpl: async (url, init) => {
      if (url.includes("/pulls/290/files")) {
        return jsonResponse([
          { filename: "prompts/definitions/_e2e/review-fix-patterns-e2e/pr-review.yaml" },
        ]);
      }
      if (url.includes("/pulls/290") && !url.includes("/files")) {
        return jsonResponse({
          number: 290,
          body: "Related to #289\nTask / Review Definition: `prompts/definitions/_e2e/review-fix-patterns-e2e/`",
          head: { ref: "docs/task-289-review-fix-patterns-e2e", repo: { full_name: "o/r" } },
        });
      }
      if (url.includes("/issues/289")) {
        return jsonResponse({ body: "" });
      }
      if (url.endsWith("/dispatches") && init?.method === "POST") {
        dispatchBody = JSON.parse(init.body);
        return { ok: true, status: 204, text: async () => "" };
      }
      throw new Error(`unexpected url: ${url}`);
    },
  });

  assert.equal(result.ok, true);
  assert.equal(result.review_definition_source, "pr_changed_files");
  assert.equal(
    result.review_definition,
    "prompts/definitions/_e2e/review-fix-patterns-e2e/pr-review.yaml",
  );
  assert.equal(dispatchBody.client_payload.ref, "docs/task-289-review-fix-patterns-e2e");
});

test("shouldSkipHarnessAutoDispatch: type: infra ラベルで skip", () => {
  const result = auto.shouldSkipHarnessAutoDispatch({
    context: "pr-created",
    pullLabels: [{ name: "type: infra" }],
    issueLabels: [],
    changedFiles: [{ filename: "apps/web/foo.ts" }],
  });
  assert.equal(result.skip, true);
  assert.equal(result.reason, "infra_pr");
});

test("shouldSkipHarnessAutoDispatch: .github/ のみ変更で skip", () => {
  const result = auto.shouldSkipHarnessAutoDispatch({
    context: "fix-ready",
    pullLabels: [],
    issueLabels: [],
    changedFiles: [{ filename: ".github/scripts/foo.cjs" }],
  });
  assert.equal(result.skip, true);
  assert.equal(result.reason, "automation_only_changes");
});

test("shouldSkipHarnessAutoDispatch: 手動 CLI（context なし）は skip しない", () => {
  const result = auto.shouldSkipHarnessAutoDispatch({
    context: "",
    pullLabels: [{ name: "type: infra" }],
    issueLabels: [],
    changedFiles: [{ filename: ".github/workflows/foo.yml" }],
  });
  assert.equal(result.skip, false);
});

test("shouldSkipFixerHarnessAutoDispatch: unit: epic ラベルで skip", () => {
  const result = auto.shouldSkipFixerHarnessAutoDispatch({
    context: "request-changes",
    pullLabels: [{ name: "unit: epic" }],
    issueLabels: [],
    changedFiles: [{ filename: "docs/foo.md" }],
    headRef: "feature/task-432-phase1-wave2",
  });
  assert.equal(result.skip, true);
  assert.equal(result.reason, "epic_pr");
});

test("shouldSkipFixerHarnessAutoDispatch: epic branch で skip", () => {
  const result = auto.shouldSkipFixerHarnessAutoDispatch({
    context: "request-changes",
    pullLabels: [],
    issueLabels: [],
    changedFiles: [{ filename: "docs/foo.md" }],
    headRef: "feature/epic-432-phase1-wave2-api-contract-foundation",
  });
  assert.equal(result.skip, true);
  assert.equal(result.reason, "epic_pr");
});

test("shouldSkipFixerHarnessAutoDispatch: Review PR harness は epic を skip しない", () => {
  const result = auto.shouldSkipHarnessAutoDispatch({
    context: "request-changes",
    pullLabels: [{ name: "unit: epic" }],
    issueLabels: [],
    changedFiles: [{ filename: "docs/foo.md" }],
  });
  assert.equal(result.skip, false);
});

test("dispatchReviewPrHarness: automation_only_changes は skipped", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "dispatch-auto-"));
  const reviewPath = "prompts/definitions/_e2e/sample/pr-review.yaml";
  write(path.join(root, reviewPath), 'definition_type: "review"\n');

  const result = await auto.dispatchReviewPrHarness({
    owner: "o",
    repo: "r",
    prNumber: 297,
    issueNumber: 289,
    definition: reviewPath,
    context: "pr-created",
    workspaceRoot: root,
    token: "token",
    fetchImpl: async (url) => {
      if (url.includes("/pulls/297/files")) {
        return jsonResponse([{ filename: ".github/scripts/dispatch-review-pr-harness.cjs" }]);
      }
      if (url.includes("/pulls/297")) {
        return jsonResponse({
          body: "Related to #289",
          head: { ref: "fix/harness", repo: { full_name: "o/r" } },
          labels: [],
        });
      }
      if (url.includes("/issues/289")) {
        return jsonResponse({ body: "", labels: [{ name: "type: docs" }] });
      }
      if (url.includes("/issues/297")) {
        return jsonResponse({ body: "Related to #289", labels: [] });
      }
      throw new Error(`unexpected url: ${url}`);
    },
  });

  assert.equal(result.ok, true);
  assert.equal(result.skipped, true);
  assert.equal(result.reason, "automation_only_changes");
});

test("dispatchReviewPrHarness: PR333再現 — task diff + ai_review_not_required で skip", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "dispatch-auto-"));
  const taskPath = "prompts/definitions/tasks/fixer-auto-dispatch/fixer-e2e-verify.yaml";
  write(
    path.join(root, taskPath),
    ['definition_type: "task"', "review:", "  ai_review_required: false"].join("\n"),
  );

  const result = await auto.dispatchReviewPrHarness({
    owner: "o",
    repo: "r",
    prNumber: 333,
    issueNumber: 331,
    context: "pr-created",
    requestedBy: "pr-created-status-sync",
    workspaceRoot: root,
    token: "token",
    fetchImpl: async (url) => {
      if (url.includes("/pulls/333/files")) {
        return jsonResponse([
          { filename: taskPath },
          { filename: "ai-logs/experiments/2026-06-02-fixer-auto-dispatch-e2e.md" },
        ]);
      }
      if (url.includes("/pulls/333") && !url.includes("/files")) {
        return jsonResponse({
          number: 333,
          body: "Related to #331",
          head: { ref: "feature/task-331-fixer-e2e-ai", repo: { full_name: "o/r" } },
          labels: [{ name: "type: test" }, { name: "area: docs" }],
        });
      }
      if (url.includes("/issues/331")) {
        return jsonResponse({ body: "### Branch summary\nfixer-e2e-ai", labels: [{ name: "area: docs" }] });
      }
      throw new Error(`unexpected url: ${url}`);
    },
  });

  assert.equal(result.ok, true);
  assert.equal(result.skipped, true);
  assert.equal(result.reason, "ai_review_not_required");
  assert.equal(result.task_definition, taskPath);
});

test("buildHarnessDirectRecoveryCommand: workflow_dispatch コマンドを生成", () => {
  const cmd = auto.buildHarnessDirectRecoveryCommand({
    owner: "o",
    repo: "r",
    prNumber: 290,
    definition: "prompts/definitions/_e2e/review-fix-patterns-e2e/pr-review.yaml",
    issueNumber: 289,
    headRef: "docs/task-289-review-fix-patterns-e2e",
  });
  assert.match(cmd, /gh workflow run "Definition Run Harness"/);
  assert.match(cmd, /target_pr=290/);
  assert.match(cmd, /ref=docs\/task-289-review-fix-patterns-e2e/);
});
