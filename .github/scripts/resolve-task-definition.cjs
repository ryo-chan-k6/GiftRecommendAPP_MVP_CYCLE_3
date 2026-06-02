"use strict";

const fs = require("node:fs");
const path = require("node:path");
const resolver = require("./resolve-review-definition.cjs");

const DEFINITION_ROOT = resolver.DEFINITION_ROOT;

function nonEmpty(value) {
  return String(value || "").trim();
}

function normalizePath(value) {
  const raw = nonEmpty(value).replace(/\\/g, "/");
  if (!raw) return "";
  return raw.startsWith(DEFINITION_ROOT) ? raw : "";
}

function readFileSafe(filePath) {
  try {
    return fs.readFileSync(filePath, "utf8");
  } catch {
    return "";
  }
}

function fileExists(filePath) {
  try {
    return fs.statSync(filePath).isFile();
  } catch {
    return false;
  }
}

function isTaskDefinitionPath(relativePath) {
  const normalized = nonEmpty(relativePath).replace(/\\/g, "/");
  if (!normalized.startsWith(`${DEFINITION_ROOT}tasks/`)) return false;
  if (normalized.endsWith(`/${resolver.REVIEW_FILE_NAME}`)) return false;
  return /\.ya?ml$/i.test(normalized);
}

function hasTaskDefinitionType(content) {
  return /definition_type:\s*["']?task["']?/i.test(String(content || ""));
}

function extractTaskDefinitionPathsFromText(text) {
  const paths = new Set();
  const body = String(text || "");

  for (const match of body.matchAll(
    /(?:\/(?:review-pr|fix-review-comments|work-issue|start-task)\s+@|Definition\s*[:：]\s*`?)([^\s`#]+\.ya?ml)`?/gi,
  )) {
    const candidate = normalizePath(match[1]);
    if (candidate && isTaskDefinitionPath(candidate)) paths.add(candidate);
  }

  for (const match of body.matchAll(/`(prompts\/definitions\/tasks\/[^`\s#]+\.ya?ml)`/g)) {
    const candidate = normalizePath(match[1]);
    if (candidate) paths.add(candidate);
  }

  return [...paths];
}

function findTaskDefinitionByFilenameSummary(workspaceRoot, summary) {
  const normalizedSummary = nonEmpty(summary).toLowerCase();
  if (!normalizedSummary) return [];
  const targetName = `${normalizedSummary}.yaml`;
  const matches = [];
  const root = path.join(workspaceRoot, `${DEFINITION_ROOT}tasks`);

  function walk(current) {
    let entries;
    try {
      entries = fs.readdirSync(current, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) {
        walk(full);
        continue;
      }
      if (entry.name.toLowerCase() !== targetName) continue;
      const relative = full.replace(/\\/g, "/").slice(workspaceRoot.replace(/\\/g, "/").length + 1);
      if (isTaskDefinitionPath(relative) && hasTaskDefinitionType(readFileSafe(full))) {
        matches.push(relative);
      }
    }
  }

  walk(root);
  return matches;
}

function pickTaskDefinitionFromChangedFiles(changedFiles, branchInfo) {
  const taskFiles = (changedFiles || [])
    .map((entry) => (typeof entry === "string" ? entry : entry?.filename || ""))
    .filter((filename) => isTaskDefinitionPath(filename));

  if (taskFiles.length === 1) {
    return taskFiles[0];
  }

  if (branchInfo?.summary) {
    const summary = branchInfo.summary.toLowerCase();
    const summaryMatches = taskFiles.filter((filename) => {
      const lower = filename.toLowerCase();
      return lower.includes(`/${summary}/`) || lower.endsWith(`/${summary}.yaml`);
    });
    if (summaryMatches.length === 1) {
      return summaryMatches[0];
    }
  }

  return "";
}

function resolveTaskDefinition({
  workspaceRoot,
  prBody = "",
  issueBody = "",
  headRef = "",
  issueNumber = null,
  definitionOverride = "",
}) {
  const workspace = nonEmpty(workspaceRoot) || process.cwd();
  const explicit = normalizePath(definitionOverride);
  if (explicit) {
    const absolute = path.join(workspace, explicit);
    if (!fileExists(absolute)) {
      return { ok: false, reason: "definition_override_missing", path: explicit };
    }
    if (!hasTaskDefinitionType(readFileSafe(absolute))) {
      return { ok: false, reason: "definition_override_not_task", path: explicit };
    }
    return { ok: true, path: explicit, source: "override" };
  }

  const fromText = [
    ...extractTaskDefinitionPathsFromText(prBody),
    ...extractTaskDefinitionPathsFromText(issueBody),
  ];
  const validFromText = [...new Set(fromText)].filter((candidate) =>
    fileExists(path.join(workspace, candidate)),
  );
  if (validFromText.length === 1) {
    return { ok: true, path: validFromText[0], source: "pr_or_issue_body" };
  }
  if (validFromText.length > 1) {
    return { ok: false, reason: "ambiguous_definition_in_text", paths: validFromText };
  }

  const branchInfo = resolver.parseBranchRef(headRef);
  const resolvedIssueNumber = issueNumber || branchInfo?.issueNumber || null;

  if (branchInfo?.summary) {
    const fromSummary = resolver.findTaskDefinitionBySummary(workspace, branchInfo.summary);
    if (fromSummary.length === 1) {
      return { ok: true, path: fromSummary[0], source: "branch_summary" };
    }
    if (fromSummary.length > 1) {
      return { ok: false, reason: "ambiguous_task_definition_by_summary", paths: fromSummary };
    }

    const fromFilename = findTaskDefinitionByFilenameSummary(workspace, branchInfo.summary);
    if (fromFilename.length === 1) {
      return { ok: true, path: fromFilename[0], source: "branch_summary_filename" };
    }
    if (fromFilename.length > 1) {
      return { ok: false, reason: "ambiguous_task_definition_by_summary", paths: fromFilename };
    }
  }

  const scored = fromSummaryCandidates(workspace, {
    issueNumber: resolvedIssueNumber,
    branchInfo,
  });

  if (scored.length === 1) {
    return { ok: true, path: scored[0].path, source: "scan", score: scored[0].score };
  }

  return {
    ok: false,
    reason: "task_definition_not_found",
    headRef,
    issueNumber: resolvedIssueNumber,
    hint: "PR 本文または Issue 本文に Task Definition パスを明示するか、--definition を指定してください。",
  };
}

function fromSummaryCandidates(workspaceRoot, { issueNumber, branchInfo }) {
  const root = path.join(workspaceRoot, `${DEFINITION_ROOT}tasks`);
  const results = [];

  function walk(current, depth = 0) {
    let entries;
    try {
      entries = fs.readdirSync(current, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) {
        walk(full, depth + 1);
        continue;
      }
      if (!/\.ya?ml$/i.test(entry.name)) continue;
      const relative = full.replace(/\\/g, "/").slice(workspaceRoot.replace(/\\/g, "/").length + 1);
      if (!isTaskDefinitionPath(relative)) continue;
      if (!hasTaskDefinitionType(readFileSafe(full))) continue;

      let score = 1;
      if (branchInfo?.summary && relative.toLowerCase().includes(`/${branchInfo.summary}/`)) {
        score += 40;
      }
      if (issueNumber && relative.includes(`task-${issueNumber}`)) {
        score += 100;
      }
      if (score > 1) results.push({ path: relative, score });
    }
  }

  walk(root);
  return results.sort((a, b) => b.score - a.score);
}

function listTaskDefinitionsByIssueNumber(workspaceRoot, issueNumber) {
  const parsed = Number(issueNumber);
  if (!Number.isInteger(parsed) || parsed <= 0) return [];
  return fromSummaryCandidates(workspaceRoot, { issueNumber: parsed, branchInfo: null })
    .filter((entry) => entry.score >= 100)
    .map((entry) => entry.path);
}

module.exports = {
  DEFINITION_ROOT,
  extractTaskDefinitionPathsFromText,
  hasTaskDefinitionType,
  isTaskDefinitionPath,
  pickTaskDefinitionFromChangedFiles,
  findTaskDefinitionByFilenameSummary,
  listTaskDefinitionsByIssueNumber,
  resolveTaskDefinition,
};
