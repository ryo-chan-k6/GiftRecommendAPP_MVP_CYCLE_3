"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");

const builder = require("./definition-run-prompt-builder.cjs");

// GitHub Push Protection 回避: リポジトリ上に secret 形式の連続文字列を置かない
function slackLikeTestToken() {
  return ["xox", "b-", "1234567890-", "abcdefghij1234567890"].join("");
}

function secretMaskingSamples() {
  return [
    slackLikeTestToken(),
    ["ghp_", "ABCDEFGHIJKLMNOPQRST"].join(""),
    ["github_pat_", "ABCDEFGHIJ_KLMNOPQRST_uv"].join(""),
    ["sk-", "ABCDEFGHIJKLMNOPQRSTUVWX"].join(""),
    ["AIza", "SyAaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"].join(""),
  ];
}

function withTempWorkspace(setup) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "defrun-test-"));
  try {
    setup(root);
    return root;
  } catch (error) {
    fs.rmSync(root, { recursive: true, force: true });
    throw error;
  }
}

function writeEpicDefinition(root, relPath = "prompts/definitions/epics/sample/epic.yaml", body) {
  const fullPath = path.join(root, relPath);
  fs.mkdirSync(path.dirname(fullPath), { recursive: true });
  fs.writeFileSync(
    fullPath,
    body ||
      [
        "schema_version: \"1.0\"",
        "definition_type: \"epic\"",
        "epic:",
        "  id: \"epic-sample\"",
        "  title: \"sample\"",
        "",
      ].join("\n"),
    "utf8",
  );
  return relPath;
}

function writeReviewDefinition(root, relPath = "prompts/definitions/_examples/review-definition.example.yaml", body) {
  const fullPath = path.join(root, relPath);
  fs.mkdirSync(path.dirname(fullPath), { recursive: true });
  fs.writeFileSync(
    fullPath,
    body ||
      [
        'schema_version: "1.0"',
        'definition_type: "review"',
        "review:",
        '  id: "review-sample"',
        '  title: "sample review"',
        "",
      ].join("\n"),
    "utf8",
  );
  return relPath;
}

test("listAllowedCommands: start-epic / review-pr / fix-review-comments", () => {
  assert.deepEqual(builder.listAllowedCommands(), ["start-epic", "review-pr", "fix-review-comments"]);
});

test("validateCommand: 未登録 Command は unsupported_command", () => {
  assert.throws(
    () => builder.validateCommand("start-task"),
    (err) => err instanceof builder.ValidationError && err.code === "unsupported_command",
  );
  assert.throws(
    () => builder.validateCommand("merge-pr"),
    (err) => err instanceof builder.ValidationError && err.code === "unsupported_command",
  );
  assert.throws(
    () => builder.validateCommand(""),
    (err) => err instanceof builder.ValidationError && err.code === "missing_input",
  );
});

test("validateRunMode: live-run は MVP で拒否", () => {
  const { registry } = builder.validateCommand("start-epic");
  assert.equal(builder.validateRunMode("dry-run", registry), "dry-run");
  assert.throws(
    () => builder.validateRunMode("live-run", registry),
    (err) => err instanceof builder.ValidationError && err.code === "run_mode_disabled",
  );
  assert.throws(
    () => builder.validateRunMode("ghost-run", registry),
    (err) => err instanceof builder.ValidationError && err.code === "invalid_run_mode",
  );
});

test("validateDefinitionPath: prompts/definitions/ 配下のみ受理", () => {
  assert.throws(
    () => builder.validateDefinitionPath("docs/some.yaml"),
    (err) => err instanceof builder.ValidationError && err.code === "invalid_definition_path",
  );
  assert.throws(
    () => builder.validateDefinitionPath("prompts/definitions/../etc/passwd"),
    (err) => err instanceof builder.ValidationError && err.code === "invalid_definition_path",
  );
  assert.throws(
    () => builder.validateDefinitionPath("prompts/definitions/foo.txt"),
    (err) => err instanceof builder.ValidationError && err.code === "invalid_definition_path",
  );
  const ok = builder.validateDefinitionPath("./prompts/definitions/epics/sample/epic.yaml");
  assert.equal(ok.definition, "prompts/definitions/epics/sample/epic.yaml");
});

test("validateDefinitionPath: workspace 指定時は実ファイル存在を検証", () => {
  const root = withTempWorkspace((dir) => {
    writeEpicDefinition(dir);
  });
  try {
    const ok = builder.validateDefinitionPath(
      "prompts/definitions/epics/sample/epic.yaml",
      { workspace: root },
    );
    assert.equal(ok.definition, "prompts/definitions/epics/sample/epic.yaml");
    assert.ok(fs.existsSync(ok.absolutePath));

    assert.throws(
      () =>
        builder.validateDefinitionPath(
          "prompts/definitions/epics/missing/epic.yaml",
          { workspace: root },
        ),
      (err) => err instanceof builder.ValidationError && err.code === "definition_not_found",
    );
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("extractDefinitionType: 先頭のトップレベル定義を読み取る", () => {
  assert.equal(builder.extractDefinitionType("definition_type: \"epic\"\n"), "epic");
  assert.equal(builder.extractDefinitionType("definition_type: task\n"), "task");
  assert.equal(builder.extractDefinitionType("schema_version: \"1.0\"\n# comment\n"), "");
});

test("validateDefinitionType: 期待値と一致しなければ mismatch", () => {
  const root = withTempWorkspace((dir) => {
    writeEpicDefinition(
      dir,
      "prompts/definitions/tasks/sample/screen-spec.yaml",
      [
        "schema_version: \"1.0\"",
        "definition_type: \"task\"",
        "",
      ].join("\n"),
    );
  });
  try {
    const taskAbs = path.join(root, "prompts/definitions/tasks/sample/screen-spec.yaml");
    assert.throws(
      () => builder.validateDefinitionType(taskAbs, "epic"),
      (err) => err instanceof builder.ValidationError && err.code === "definition_type_mismatch",
    );
    assert.equal(builder.validateDefinitionType(taskAbs, "task"), "task");
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("validateDefinitionType: fix-review-comments は contract を許容", () => {
  const root = withTempWorkspace((dir) => {
    const rel = "prompts/definitions/contracts/sample/openapi-fragment.yaml";
    const full = path.join(dir, rel);
    fs.mkdirSync(path.dirname(full), { recursive: true });
    fs.writeFileSync(full, 'definition_type: "contract"\n', "utf8");
  });
  try {
    const abs = path.join(root, "prompts/definitions/contracts/sample/openapi-fragment.yaml");
    assert.equal(builder.validateDefinitionType(abs, ["task", "contract"]), "contract");
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("buildDefinitionRunRequest: fix-review-comments + contract definition", () => {
  const root = withTempWorkspace((dir) => {
    const rel = "prompts/definitions/contracts/sample/openapi-fragment.yaml";
    const full = path.join(dir, rel);
    fs.mkdirSync(path.dirname(full), { recursive: true });
    fs.writeFileSync(full, 'definition_type: "contract"\n', "utf8");
  });
  try {
    const request = builder.buildDefinitionRunRequest(
      {
        command: "fix-review-comments",
        definition: "prompts/definitions/contracts/sample/openapi-fragment.yaml",
        run_mode: "live-run",
        target_pr: "417",
      },
      { workspace: root },
    );
    assert.equal(request.definition_type, "contract");
    assert.match(request.prompt, /openapi-fragment\.yaml/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("validateDefinitionType: definition_type 欠落は missing", () => {
  const root = withTempWorkspace((dir) => {
    const rel = "prompts/definitions/epics/no-type/epic.yaml";
    const full = path.join(dir, rel);
    fs.mkdirSync(path.dirname(full), { recursive: true });
    fs.writeFileSync(full, "schema_version: \"1.0\"\nepic:\n  id: x\n", "utf8");
  });
  try {
    const abs = path.join(root, "prompts/definitions/epics/no-type/epic.yaml");
    assert.throws(
      () => builder.validateDefinitionType(abs, "epic"),
      (err) => err instanceof builder.ValidationError && err.code === "definition_type_missing",
    );
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("buildPrompt: 主要キーワードと禁止条項を含む", () => {
  const text = builder.buildPrompt({
    command: "start-epic",
    definition: "prompts/definitions/epics/sample/epic.yaml",
    run_mode: "dry-run",
    output_section: "dry-run 実行時",
  });
  assert.match(text, /Definition Run/);
  assert.match(text, /\/start-epic/);
  assert.match(text, /@prompts\/definitions\/epics\/sample\/epic.yaml/);
  assert.match(text, /run_mode: dry-run/);
  assert.match(text, /gh CLI \/ git push \/ GitHub API の write 系操作は全面禁止/);
  assert.match(text, /Agent は `gh project item-edit`/);
  assert.match(text, /Harness は同期処理を行わない/);
  assert.match(text, /「dry-run 実行時」セクション/);
});

test("buildDefinitionRunRequest: 正常系で完全プロンプトを返す", () => {
  const root = withTempWorkspace((dir) => {
    writeEpicDefinition(dir);
  });
  try {
    const result = builder.buildDefinitionRunRequest(
      {
        command: "start-epic",
        definition: "prompts/definitions/epics/sample/epic.yaml",
        run_mode: "dry-run",
        requested_by: "ryo-c via Slack",
        request_issue: "42",
      },
      { workspace: root },
    );
    assert.equal(result.command, "start-epic");
    assert.equal(result.definition, "prompts/definitions/epics/sample/epic.yaml");
    assert.equal(result.run_mode, "dry-run");
    assert.equal(result.definition_type, "epic");
    assert.equal(result.ref, "develop");
    assert.equal(result.requested_by, "ryo-c via Slack");
    assert.equal(result.request_issue, "42");
    assert.equal(result.output_section, "dry-run 実行時");
    assert.match(result.prompt, /\/start-epic/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("buildDefinitionRunRequest: definition 不在は definition_not_found", () => {
  const root = withTempWorkspace(() => {});
  try {
    assert.throws(
      () =>
        builder.buildDefinitionRunRequest(
          {
            command: "start-epic",
            definition: "prompts/definitions/epics/missing/epic.yaml",
            run_mode: "dry-run",
          },
          { workspace: root },
        ),
      (err) => err instanceof builder.ValidationError && err.code === "definition_not_found",
    );
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("buildDefinitionRunRequest: live-run は run_mode_disabled", () => {
  const root = withTempWorkspace((dir) => writeEpicDefinition(dir));
  try {
    assert.throws(
      () =>
        builder.buildDefinitionRunRequest(
          {
            command: "start-epic",
            definition: "prompts/definitions/epics/sample/epic.yaml",
            run_mode: "live-run",
          },
          { workspace: root },
        ),
      (err) => err instanceof builder.ValidationError && err.code === "run_mode_disabled",
    );
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("maskSecrets: 既知 secret prefix を *** に置換する", () => {
  const samples = secretMaskingSamples();
  for (const sample of samples) {
    assert.equal(builder.maskSecrets(`token=${sample}`), "token=***", `should mask: ${sample}`);
  }
  assert.equal(builder.maskSecrets(""), "");
  assert.equal(builder.maskSecrets(null), "");
  assert.equal(builder.maskSecrets("hello"), "hello");
});

test("sanitizeRequestedBy: 改行除去と長さ制限", () => {
  assert.equal(builder.sanitizeRequestedBy("ryo-c\nvia\rslack"), "ryo-c via slack");
  assert.equal(builder.sanitizeRequestedBy(undefined), "");
  const long = "x".repeat(500);
  assert.equal(builder.sanitizeRequestedBy(long, 10).length, 10);
});

test("sanitizeRequestedBy: secret らしき文字列はマスク", () => {
  assert.equal(builder.sanitizeRequestedBy(`user ${slackLikeTestToken()}`), "user ***");
});

test("sanitizeRequestIssue: #数値 または 数値 のみ受理", () => {
  assert.equal(builder.sanitizeRequestIssue("123"), "123");
  assert.equal(builder.sanitizeRequestIssue("#456"), "456");
  assert.equal(builder.sanitizeRequestIssue(""), "");
  assert.equal(builder.sanitizeRequestIssue(undefined), "");
  assert.throws(
    () => builder.sanitizeRequestIssue("abc"),
    (err) => err instanceof builder.ValidationError && err.code === "invalid_request_issue",
  );
  assert.throws(
    () => builder.sanitizeRequestIssue("-1"),
    (err) => err instanceof builder.ValidationError && err.code === "invalid_request_issue",
  );
});

test("decisionLine: 主要フィールドを 1 行に整形してマスクする", () => {
  const line = builder.decisionLine("validated", {
    command: "start-epic",
    run_mode: "dry-run",
    secret_field: "ghp_ABCDEFGHIJKLMNOPQRSTUV",
  });
  assert.match(line, /^decision: validated /);
  assert.match(line, /command=start-epic/);
  assert.match(line, /run_mode=dry-run/);
  assert.match(line, /secret_field=\*\*\*/);
});

test("summarizeForLog: 必要フィールドだけ返す", () => {
  const root = withTempWorkspace((dir) => writeEpicDefinition(dir));
  try {
    const request = builder.buildDefinitionRunRequest(
      {
        command: "start-epic",
        definition: "prompts/definitions/epics/sample/epic.yaml",
        run_mode: "dry-run",
      },
      { workspace: root },
    );
    const summary = builder.summarizeForLog(request);
    assert.equal(summary.command, "start-epic");
    assert.equal(summary.run_mode, "dry-run");
    assert.equal(summary.definition_type, "epic");
    assert.deepEqual(summary.allowed_commands, ["start-epic", "review-pr", "fix-review-comments"]);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("review-pr: live-run は target_pr 必須", () => {
  const root = withTempWorkspace((dir) => writeReviewDefinition(dir));
  try {
    assert.throws(
      () =>
        builder.buildDefinitionRunRequest(
          {
            command: "review-pr",
            definition: "prompts/definitions/_examples/review-definition.example.yaml",
            run_mode: "live-run",
          },
          { workspace: root },
        ),
      (err) => err instanceof builder.ValidationError && err.code === "missing_target_pr",
    );
    const request = builder.buildDefinitionRunRequest(
      {
        command: "review-pr",
        definition: "prompts/definitions/_examples/review-definition.example.yaml",
        run_mode: "live-run",
        target_pr: "282",
      },
      { workspace: root },
    );
    assert.equal(request.target_pr, "282");
    assert.match(request.prompt, /publish-ai-review-and-dispatch/);
    assert.match(request.prompt, /対象PR: #282/);
    assert.match(request.prompt, /逐語で出力/);
    assert.match(request.prompt, /本文を代替してはならない/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("review-pr: dry-run は target_pr なしでも受理", () => {
  const root = withTempWorkspace((dir) => writeReviewDefinition(dir));
  try {
    const request = builder.buildDefinitionRunRequest(
      {
        command: "review-pr",
        definition: "prompts/definitions/_examples/review-definition.example.yaml",
        run_mode: "dry-run",
      },
      { workspace: root },
    );
    assert.equal(request.run_mode, "dry-run");
    assert.match(request.prompt, /PR コメント投稿・repository_dispatch・Projects Status 更新を行わない/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
