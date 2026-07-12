"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const harness = require("./dispatch-definition-run.cjs");
const fixer = require("./dispatch-fix-review-harness.cjs");
const taskResolver = require("./resolve-task-definition.cjs");

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

test("resolveTaskDefinition: branch summary から Task Definition を解決", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "task-def-"));
  const taskPath = "prompts/definitions/tasks/fixer-auto-dispatch/fixer-dispatch-script.yaml";
  write(
    path.join(root, taskPath),
    'definition_type: "task"\ntask:\n  id: "task-fixer-dispatch-script"\n',
  );

  const result = taskResolver.resolveTaskDefinition({
    workspaceRoot: root,
    headRef: "feature/task-324-fixer-dispatch-script",
    issueNumber: 324,
  });

  assert.equal(result.ok, true);
  assert.equal(result.path, taskPath);
  assert.equal(result.source, "branch_summary_filename");
});

test("dispatchFixReviewHarness: Task Definition 解決成功時に fix-review-comments を dispatch", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "fix-dispatch-"));
  const taskPath = "prompts/definitions/tasks/fixer-auto-dispatch/fixer-dispatch-script.yaml";
  write(path.join(root, taskPath), 'definition_type: "task"\ntask:\n  id: "task-fixer-dispatch-script"\n');

  let dispatchBody = null;
  const result = await fixer.dispatchFixReviewHarness({
    owner: "o",
    repo: "r",
    prNumber: 324,
    issueNumber: 324,
    definition: taskPath,
    requestedBy: "test",
    context: "request-changes",
    workspaceRoot: root,
    token: "token",
    fetchImpl: async (url, init) => {
      if (url.includes("/pulls/324/files")) {
        return jsonResponse([{ filename: "docs/06_実装設計/github_actions/Fixer自動dispatch設計書.md" }]);
      }
      if (url.includes("/pulls/324") && !url.includes("/files")) {
        return jsonResponse({
          body: "Related to #324",
          head: { ref: "feature/task-324-fixer-dispatch-script", repo: { full_name: "o/r" } },
          labels: [],
        });
      }
      if (url.includes("/issues/324")) {
        return jsonResponse({ body: "", labels: [{ name: "type: feature" }] });
      }
      if (url.endsWith("/dispatches") && init?.method === "POST") {
        dispatchBody = JSON.parse(init.body);
        return { ok: true, status: 204, text: async () => "" };
      }
      throw new Error(`unexpected url: ${url}`);
    },
  });

  assert.equal(result.ok, true);
  assert.equal(result.task_definition, taskPath);
  assert.equal(dispatchBody.event_type, "definition-run");
  assert.equal(dispatchBody.client_payload.command, "fix-review-comments");
  assert.equal(dispatchBody.client_payload.definition, taskPath);
  assert.equal(dispatchBody.client_payload.target_pr, "324");
  assert.equal(dispatchBody.client_payload.ref, "feature/task-324-fixer-dispatch-script");
  assert.match(result.recovery_command, /dispatch-fix-review-harness\.cjs/);
});

test("dispatchFixReviewHarness: Epic PR（unit: epic ラベル）で skip", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "fix-dispatch-"));
  const epicPath = "prompts/definitions/epics/phase1-wave2-api-contract-foundation/epic.yaml";
  write(path.join(root, epicPath), 'definition_type: "epic"\n');

  const result = await fixer.dispatchFixReviewHarness({
    owner: "o",
    repo: "r",
    prNumber: 433,
    issueNumber: 432,
    context: "request-changes",
    workspaceRoot: root,
    token: "token",
    fetchImpl: async (url) => {
      if (url.includes("/pulls/433/files")) {
        return jsonResponse([{ filename: "docs/foo.md" }]);
      }
      if (url.includes("/pulls/433")) {
        return jsonResponse({
          body: "Related to #432",
          head: { ref: "feature/epic-432-phase1-wave2-api-contract-foundation", repo: { full_name: "o/r" } },
          labels: [{ name: "unit: epic" }],
        });
      }
      if (url.includes("/issues/432")) {
        return jsonResponse({ body: "", labels: [{ name: "unit: epic" }] });
      }
      throw new Error(`unexpected url: ${url}`);
    },
  });

  assert.equal(result.ok, true);
  assert.equal(result.skipped, true);
  assert.equal(result.reason, "epic_pr");
});

test("dispatchFixReviewHarness: Epic PR（epic branch のみ）で skip", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "fix-dispatch-"));

  const result = await fixer.dispatchFixReviewHarness({
    owner: "o",
    repo: "r",
    prNumber: 433,
    issueNumber: 432,
    context: "request-changes",
    workspaceRoot: root,
    token: "token",
    fetchImpl: async (url) => {
      if (url.includes("/pulls/433/files")) {
        return jsonResponse([{ filename: "docs/foo.md" }]);
      }
      if (url.includes("/pulls/433")) {
        return jsonResponse({
          body: "Related to #432",
          head: { ref: "feature/epic-432-phase1-wave2-api-contract-foundation", repo: { full_name: "o/r" } },
          labels: [],
        });
      }
      if (url.includes("/issues/432")) {
        return jsonResponse({ body: "", labels: [{ name: "type: feature" }] });
      }
      if (url.includes("/issues/433")) {
        return jsonResponse({ body: "", labels: [] });
      }
      throw new Error(`unexpected url: ${url}`);
    },
  });

  assert.equal(result.ok, true);
  assert.equal(result.skipped, true);
  assert.equal(result.reason, "epic_pr");
});

test("dispatchFixReviewHarness: infra ラベルで skip（request-changes context）", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "fix-dispatch-"));
  const taskPath = "prompts/definitions/tasks/fixer-auto-dispatch/fixer-dispatch-script.yaml";
  write(path.join(root, taskPath), 'definition_type: "task"\n');

  const result = await fixer.dispatchFixReviewHarness({
    owner: "o",
    repo: "r",
    prNumber: 324,
    issueNumber: 324,
    definition: taskPath,
    context: "request-changes",
    workspaceRoot: root,
    token: "token",
    fetchImpl: async (url) => {
      if (url.includes("/pulls/324/files")) {
        return jsonResponse([{ filename: "docs/foo.md" }]);
      }
      if (url.includes("/pulls/324")) {
        return jsonResponse({
          body: "Related to #324",
          head: { ref: "feature/task-324-fixer-dispatch-script", repo: { full_name: "o/r" } },
          labels: [],
        });
      }
      if (url.includes("/issues/324")) {
        return jsonResponse({ body: "", labels: [{ name: "area: infra" }] });
      }
      throw new Error(`unexpected url: ${url}`);
    },
  });

  assert.equal(result.ok, true);
  assert.equal(result.skipped, true);
  assert.equal(result.reason, "infra_pr");
});

test("dispatchFixReviewHarness: Task Definition 解決失敗時 recovery_command を返す", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "fix-dispatch-"));

  const result = await fixer.dispatchFixReviewHarness({
    owner: "o",
    repo: "r",
    prNumber: 999,
    issueNumber: 999,
    context: "request-changes",
    workspaceRoot: root,
    token: "token",
    fetchImpl: async (url) => {
      if (url.includes("/pulls/999/files")) {
        return jsonResponse([]);
      }
      if (url.includes("/pulls/999")) {
        return jsonResponse({
          body: "Related to #999",
          head: { ref: "feature/task-999-unknown", repo: { full_name: "o/r" } },
          labels: [],
        });
      }
      if (url.includes("/issues/999")) {
        return jsonResponse({ body: "", labels: [] });
      }
      throw new Error(`unexpected url: ${url}`);
    },
  });

  assert.equal(result.ok, false);
  assert.equal(result.reason, "task_definition_not_found");
  assert.match(result.recovery_command, /dispatch-fix-review-harness\.cjs/);
});

test("buildHarnessDirectRecoveryCommand: fix-review-comments workflow コマンド", () => {
  const taskPath = "prompts/definitions/tasks/fixer-auto-dispatch/fixer-dispatch-script.yaml";
  const cmd = fixer.buildHarnessDirectRecoveryCommand({
    owner: "o",
    repo: "r",
    prNumber: 324,
    definition: taskPath,
    issueNumber: 324,
    headRef: "feature/task-324-fixer-dispatch-script",
  });
  assert.match(cmd, /command=fix-review-comments/);
  assert.match(cmd, /target_pr=324/);
});

test("buildClientPayload: fix-review-comments live-run payload", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "dispatch-run-"));
  const definition = "prompts/definitions/tasks/fixer-auto-dispatch/fixer-dispatch-script.yaml";
  write(path.join(root, definition), 'definition_type: "task"\n');
  const payload = harness.buildClientPayload({
    command: "fix-review-comments",
    definition,
    runMode: "live-run",
    targetPr: "324",
    requestIssue: "324",
    requestedBy: "request-changes-status-sync",
    workspaceRoot: root,
  });
  assert.equal(payload.command, "fix-review-comments");
  assert.equal(payload.run_mode, "live-run");
  assert.equal(payload.target_pr, "324");
});

test("dispatchFixReviewHarness: Contract Task PR から fix-review-comments を dispatch", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "fix-dispatch-contract-"));
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

  let dispatchBody = null;
  const result = await fixer.dispatchFixReviewHarness({
    owner: "o",
    repo: "r",
    prNumber: 417,
    issueNumber: 416,
    context: "request-changes",
    workspaceRoot: root,
    token: "token",
    fetchImpl: async (url, init) => {
      if (url.includes("/pulls/417/files")) {
        return jsonResponse([
          { filename: "packages/contracts/openapi/public-api.yaml" },
          { filename: contractPath },
          { filename: reviewPath },
        ]);
      }
      if (url.includes("/pulls/417") && !url.includes("/files")) {
        return jsonResponse({
          body: [
            "| Definition | `prompts/definitions/contracts/api-pub-003-item-detail/openapi-fragment.yaml` |",
            "Related to #416",
          ].join("\n"),
          head: { ref: "feature/task-416-pub-003-item-detail-openapi", repo: { full_name: "o/r" } },
          labels: [],
        });
      }
      if (url.includes("/issues/416")) {
        return jsonResponse({
          body: `Contract Definition\n\`${contractPath}\``,
          labels: [{ name: "type: feature" }],
        });
      }
      if (url.includes("/issues/417")) {
        return jsonResponse({
          body: "Related to #416",
          labels: [{ name: "type: feature" }],
        });
      }
      if (url.endsWith("/dispatches") && init?.method === "POST") {
        dispatchBody = JSON.parse(init.body);
        return { ok: true, status: 204, text: async () => "" };
      }
      throw new Error(`unexpected url: ${url}`);
    },
  });

  assert.equal(result.ok, true);
  assert.equal(result.task_definition, contractPath);
  assert.equal(dispatchBody.client_payload.command, "fix-review-comments");
  assert.equal(dispatchBody.client_payload.definition, contractPath);
});
