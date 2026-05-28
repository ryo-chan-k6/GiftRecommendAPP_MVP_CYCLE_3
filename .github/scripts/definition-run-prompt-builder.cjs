"use strict";

const fs = require("node:fs");
const path = require("node:path");

const DEFINITION_PATH_PREFIX = "prompts/definitions/";
const DEFAULT_REQUESTED_BY_MAX_LENGTH = 200;
const DEFAULT_REQUEST_ISSUE_MAX = 1_000_000;

const COMMAND_REGISTRY = Object.freeze({
  "start-epic": Object.freeze({
    definition_type: "epic",
    default_ref: "develop",
    dry_run_supported: true,
    live_run_supported: false,
    output_section: "dry-run 実行時",
  }),
});

const SUPPORTED_RUN_MODES = Object.freeze(["dry-run", "live-run"]);

const SECRET_PATTERNS = Object.freeze([
  /xox[abprs]-[A-Za-z0-9-]{10,}/g,
  /ghp_[A-Za-z0-9]{20,}/g,
  /gho_[A-Za-z0-9]{20,}/g,
  /ghu_[A-Za-z0-9]{20,}/g,
  /ghs_[A-Za-z0-9]{20,}/g,
  /ghr_[A-Za-z0-9]{20,}/g,
  /github_pat_[A-Za-z0-9_]{20,}/g,
  /sk-[A-Za-z0-9]{20,}/g,
  /key-[A-Za-z0-9]{20,}/g,
  /cur_[A-Za-z0-9_-]{20,}/g,
  /AIza[0-9A-Za-z_-]{30,}/g,
  /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----/g,
]);

const SECRET_PLACEHOLDER = "***";

class ValidationError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "ValidationError";
    this.code = code;
  }
}

function listAllowedCommands() {
  return Object.keys(COMMAND_REGISTRY);
}

function getCommandRegistryEntry(command) {
  return COMMAND_REGISTRY[command] || null;
}

function maskSecrets(value) {
  if (value == null) return "";
  let text = String(value);
  for (const pattern of SECRET_PATTERNS) {
    text = text.replace(pattern, SECRET_PLACEHOLDER);
  }
  return text;
}

function sanitizeRequestedBy(value, maxLength = DEFAULT_REQUESTED_BY_MAX_LENGTH) {
  const raw = value == null ? "" : String(value);
  const stripped = raw.replace(/[\r\n\t]/g, " ").trim();
  if (!stripped) return "";
  const limited = stripped.slice(0, Math.max(1, maxLength));
  return maskSecrets(limited);
}

function sanitizeRequestIssue(value) {
  if (value == null) return "";
  const text = String(value).trim();
  if (!text) return "";
  if (!/^\#?\d+$/.test(text)) {
    throw new ValidationError("invalid_request_issue", "request_issue must be a positive integer or #<num>.");
  }
  const numeric = Number(text.replace(/^#/, ""));
  if (!Number.isFinite(numeric) || numeric <= 0 || numeric > DEFAULT_REQUEST_ISSUE_MAX) {
    throw new ValidationError("invalid_request_issue", "request_issue is out of range.");
  }
  return String(numeric);
}

function ensurePresent(name, value) {
  if (value == null || String(value).trim() === "") {
    throw new ValidationError("missing_input", `Required input "${name}" is missing.`);
  }
}

function validateCommand(command) {
  ensurePresent("command", command);
  const trimmed = String(command).trim();
  const entry = getCommandRegistryEntry(trimmed);
  if (!entry) {
    throw new ValidationError(
      "unsupported_command",
      `command "${trimmed}" is not registered. allowed: ${listAllowedCommands().join(", ")}`,
    );
  }
  return { command: trimmed, registry: entry };
}

function validateRunMode(runMode, registryEntry) {
  ensurePresent("run_mode", runMode);
  const trimmed = String(runMode).trim();
  if (!SUPPORTED_RUN_MODES.includes(trimmed)) {
    throw new ValidationError(
      "invalid_run_mode",
      `run_mode "${trimmed}" is not supported. allowed: ${SUPPORTED_RUN_MODES.join(", ")}`,
    );
  }
  if (trimmed === "dry-run" && !registryEntry.dry_run_supported) {
    throw new ValidationError("run_mode_disabled", `dry-run is disabled for this command.`);
  }
  if (trimmed === "live-run" && !registryEntry.live_run_supported) {
    throw new ValidationError(
      "run_mode_disabled",
      `live-run is not allowed for this command in the current MVP.`,
    );
  }
  return trimmed;
}

function validateDefinitionPath(definition, { workspace } = {}) {
  ensurePresent("definition", definition);
  const trimmed = String(definition).trim();
  const normalized = trimmed.replace(/\\/g, "/").replace(/^\.\//, "");
  if (normalized.includes("..")) {
    throw new ValidationError(
      "invalid_definition_path",
      `definition path must not contain ".." segments: ${trimmed}`,
    );
  }
  if (!normalized.startsWith(DEFINITION_PATH_PREFIX)) {
    throw new ValidationError(
      "invalid_definition_path",
      `definition path must start with "${DEFINITION_PATH_PREFIX}": ${trimmed}`,
    );
  }
  if (!/\.(ya?ml)$/i.test(normalized)) {
    throw new ValidationError(
      "invalid_definition_path",
      `definition path must end with .yaml or .yml: ${trimmed}`,
    );
  }
  let exists = true;
  let absolute = normalized;
  if (workspace) {
    absolute = path.join(workspace, normalized);
    try {
      const stat = fs.statSync(absolute);
      exists = stat.isFile();
    } catch {
      exists = false;
    }
    if (!exists) {
      throw new ValidationError("definition_not_found", `definition file does not exist: ${normalized}`);
    }
  }
  return { definition: normalized, absolutePath: absolute };
}

function extractDefinitionType(yamlText) {
  const text = String(yamlText || "");
  const match = text.match(/^\s*definition_type\s*:\s*['"]?([A-Za-z0-9_-]+)['"]?\s*$/m);
  return match ? match[1].trim() : "";
}

function validateDefinitionType(absolutePath, expectedType, { fsImpl = fs } = {}) {
  let yamlText = "";
  try {
    yamlText = fsImpl.readFileSync(absolutePath, "utf8");
  } catch (error) {
    throw new ValidationError(
      "definition_not_readable",
      `definition file is not readable: ${absolutePath}: ${error.message}`,
    );
  }
  const actual = extractDefinitionType(yamlText);
  if (!actual) {
    throw new ValidationError(
      "definition_type_missing",
      `definition_type is missing in: ${absolutePath}`,
    );
  }
  if (actual !== expectedType) {
    throw new ValidationError(
      "definition_type_mismatch",
      `definition_type mismatch: expected "${expectedType}", got "${actual}" in ${absolutePath}`,
    );
  }
  return actual;
}

function buildPrompt({ command, definition, run_mode, output_section }) {
  return [
    "このリポジトリで Definition Run を実行する。",
    "",
    "遵守:",
    "- AGENTS.md",
    "- .cursor/rules/*.mdc",
    `- .cursor/commands/${command}.md`,
    "",
    `実行コマンド: /${command}`,
    `対象Definition: @${definition}`,
    `run_mode: ${run_mode}`,
    "",
    "run_mode が dry-run の場合、Issue / Branch / Project / PR / Label / Definition への",
    "あらゆる書き込みを行わない。gh CLI / git push / GitHub API の write 系操作は全面禁止。",
    "Agent は `gh project item-edit` 等で Projects を直接更新せず、",
    "`git push` のみで Branch 運用状態を確定しない。",
    "Issue 作成・更新後の同期は既存 workflow が行うため、Harness は同期処理を行わない。",
    "",
    `結果は .cursor/commands/${command}.md の「${output_section}」セクションのフォーマットで出力する。`,
    "",
  ].join("\n");
}

function buildDefinitionRunRequest(rawInput = {}, { workspace, fsImpl } = {}) {
  const { command, registry } = validateCommand(rawInput.command);
  const runMode = validateRunMode(rawInput.run_mode, registry);
  const { definition, absolutePath } = validateDefinitionPath(rawInput.definition, { workspace });
  const detectedType = workspace
    ? validateDefinitionType(absolutePath, registry.definition_type, { fsImpl })
    : registry.definition_type;
  const requestedBy = sanitizeRequestedBy(rawInput.requested_by);
  const requestIssue = sanitizeRequestIssue(rawInput.request_issue);
  const ref = String(rawInput.ref || registry.default_ref || "develop").trim();

  const prompt = buildPrompt({
    command,
    definition,
    run_mode: runMode,
    output_section: registry.output_section,
  });

  const maskedPrompt = maskSecrets(prompt);

  return {
    command,
    definition,
    definition_absolute_path: absolutePath,
    definition_type: detectedType,
    run_mode: runMode,
    requested_by: requestedBy,
    request_issue: requestIssue,
    ref,
    output_section: registry.output_section,
    prompt: maskedPrompt,
    registry_entry: registry,
  };
}

function summarizeForLog(request) {
  if (!request) return {};
  return {
    command: request.command,
    definition: request.definition,
    definition_type: request.definition_type,
    run_mode: request.run_mode,
    ref: request.ref,
    requested_by: request.requested_by || "-",
    request_issue: request.request_issue || "-",
    output_section: request.output_section,
    allowed_commands: listAllowedCommands(),
  };
}

function decisionLine(label, fields = {}) {
  const parts = Object.entries(fields)
    .filter(([, value]) => value != null && String(value).trim() !== "")
    .map(([key, value]) => `${key}=${maskSecrets(String(value)).replace(/\s+/g, " ")}`);
  return `decision: ${label} ${parts.join(" ")}`.trim();
}

module.exports = {
  COMMAND_REGISTRY,
  DEFINITION_PATH_PREFIX,
  SUPPORTED_RUN_MODES,
  SECRET_PLACEHOLDER,
  ValidationError,
  buildDefinitionRunRequest,
  buildPrompt,
  decisionLine,
  extractDefinitionType,
  getCommandRegistryEntry,
  listAllowedCommands,
  maskSecrets,
  sanitizeRequestIssue,
  sanitizeRequestedBy,
  summarizeForLog,
  validateCommand,
  validateDefinitionPath,
  validateDefinitionType,
  validateRunMode,
};
