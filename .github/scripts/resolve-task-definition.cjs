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

function isContractDefinitionPath(relativePath) {
  const normalized = nonEmpty(relativePath).replace(/\\/g, "/");
  if (!normalized.startsWith(`${DEFINITION_ROOT}contracts/`)) return false;
  if (normalized.endsWith(`/${resolver.REVIEW_FILE_NAME}`)) return false;
  return /\.ya?ml$/i.test(normalized);
}

function hasContractDefinitionType(content) {
  return /definition_type:\s*["']?contract["']?/i.test(String(content || ""));
}

function isHarnessDefinitionFile(relativePath, content) {
  if (isTaskDefinitionPath(relativePath) && hasTaskDefinitionType(content)) return "task";
  if (isContractDefinitionPath(relativePath) && hasContractDefinitionType(content)) return "contract";
  return "";
}

function extractYamlScalar(content, key) {
  const pattern = new RegExp(`^\\s*${key}:\\s*"?([^"\\n#]+)"?`, "m");
  const match = pattern.exec(String(content || ""));
  return match ? nonEmpty(match[1]) : "";
}

function extractLinkedContractFromReviewContent(reviewContent) {
  const targetBlock = /target:\s*[\s\S]*?(?=\n[a-z_]+:|\n\S|\s*$)/i.exec(String(reviewContent || ""));
  const block = targetBlock ? targetBlock[0] : reviewContent;
  return normalizePath(extractYamlScalar(block, "task_definition"));
}

function extractContractDefinitionPathsFromText(text) {
  const paths = new Set();
  const body = String(text || "");

  for (const match of body.matchAll(
    /(?:Contract Definition|ContractDefinition)\s*[:：]\s*`?([^\s`#]+\.ya?ml)`?/gi,
  )) {
    const candidate = normalizePath(match[1]);
    if (candidate && isContractDefinitionPath(candidate)) paths.add(candidate);
  }

  for (const match of body.matchAll(
    /(?:Definition\s*[:：]\s*`?)(prompts\/definitions\/contracts\/[^\s`#]+\.ya?ml)`?/gi,
  )) {
    const candidate = normalizePath(match[1]);
    if (candidate) paths.add(candidate);
  }

  for (const match of body.matchAll(/`(prompts\/definitions\/contracts\/[^`\s#]+\.ya?ml)`/g)) {
    const candidate = normalizePath(match[1]);
    if (candidate) paths.add(candidate);
  }

  for (const match of body.matchAll(/\/create-contract-task\s+@([^\s#`]+\.ya?ml)/gi)) {
    const candidate = normalizePath(match[1]);
    if (candidate && isContractDefinitionPath(candidate)) paths.add(candidate);
  }

  return [...paths];
}

function preferOpenApiFragmentDefinitionPath(paths) {
  const list = [...new Set(paths || [])];
  if (list.length <= 1) return list[0] || "";
  const fragmentPaths = list.filter((candidate) => /\/openapi-fragment\.ya?ml$/i.test(candidate));
  if (fragmentPaths.length === 1) return fragmentPaths[0];
  return "";
}

function pickContractDefinitionFromChangedFiles(changedFiles, branchInfo, workspaceRoot) {
  const workspace = nonEmpty(workspaceRoot) || process.cwd();
  const contractFiles = (changedFiles || [])
    .map((entry) => (typeof entry === "string" ? entry : entry?.filename || ""))
    .filter((filename) => isContractDefinitionPath(filename));

  const valid = contractFiles.filter((filename) => {
    const kind = isHarnessDefinitionFile(filename, readFileSafe(path.join(workspace, filename)));
    return kind === "contract";
  });

  if (valid.length === 1) {
    return valid[0];
  }

  const fragmentPick = preferOpenApiFragmentDefinitionPath(valid);
  if (fragmentPick) return fragmentPick;

  if (branchInfo?.summary) {
    const summary = branchInfo.summary.toLowerCase();
    const summaryMatches = valid.filter((filename) => filename.toLowerCase().includes(`/${summary}/`));
    if (summaryMatches.length === 1) {
      return summaryMatches[0];
    }
    const fragmentFromSummary = preferOpenApiFragmentDefinitionPath(summaryMatches);
    if (fragmentFromSummary) return fragmentFromSummary;
  }

  return "";
}

function pickContractDefinitionFromReviewPaths(reviewPaths, workspaceRoot) {
  const workspace = nonEmpty(workspaceRoot) || process.cwd();
  const linked = new Set();

  for (const reviewPath of reviewPaths) {
    const normalized = normalizePath(reviewPath);
    if (!normalized || !normalized.endsWith(`/${resolver.REVIEW_FILE_NAME}`)) continue;
    const absolute = path.join(workspace, normalized);
    if (!fileExists(absolute)) continue;
    const contractPath = extractLinkedContractFromReviewContent(readFileSafe(absolute));
    if (!contractPath || !isContractDefinitionPath(contractPath)) continue;
    if (!fileExists(path.join(workspace, contractPath))) continue;
    if (!hasContractDefinitionType(readFileSafe(path.join(workspace, contractPath)))) continue;
    linked.add(contractPath);
  }

  const list = [...linked];
  if (list.length === 1) return list[0];
  const fragmentPick = preferOpenApiFragmentDefinitionPath(list);
  if (fragmentPick) return fragmentPick;
  return "";
}

function pickContractDefinitionFromReviewChangedFiles(changedFiles, workspaceRoot, branchInfo) {
  const reviewFiles = (changedFiles || [])
    .map((entry) => (typeof entry === "string" ? entry : entry?.filename || ""))
    .filter(
      (filename) =>
        filename.startsWith(`${DEFINITION_ROOT}reviews/`) &&
        filename.endsWith(`/${resolver.REVIEW_FILE_NAME}`),
    );

  if (reviewFiles.length === 0) return "";

  if (reviewFiles.length === 1) {
    return pickContractDefinitionFromReviewPaths(reviewFiles, workspaceRoot);
  }

  if (branchInfo?.summary) {
    const summary = branchInfo.summary.toLowerCase();
    const summaryMatches = reviewFiles.filter((filename) => filename.toLowerCase().includes(`/${summary}/`));
    if (summaryMatches.length === 1) {
      return pickContractDefinitionFromReviewPaths(summaryMatches, workspaceRoot);
    }
  }

  return pickContractDefinitionFromReviewPaths(reviewFiles, workspaceRoot);
}

function resolveContractDefinition({
  workspaceRoot,
  prBody = "",
  issueBody = "",
  headRef = "",
  changedFiles = [],
}) {
  const workspace = nonEmpty(workspaceRoot) || process.cwd();
  const branchInfo = resolver.parseBranchRef(headRef);

  const fromText = [
    ...extractContractDefinitionPathsFromText(prBody),
    ...extractContractDefinitionPathsFromText(issueBody),
  ];
  const validFromText = [...new Set(fromText)].filter((candidate) => {
    const absolute = path.join(workspace, candidate);
    return fileExists(absolute) && hasContractDefinitionType(readFileSafe(absolute));
  });
  if (validFromText.length === 1) {
    return { ok: true, path: validFromText[0], source: "pr_or_issue_body_contract", definition_kind: "contract" };
  }
  if (validFromText.length > 1) {
    const fragmentPick = preferOpenApiFragmentDefinitionPath(validFromText);
    if (fragmentPick) {
      return { ok: true, path: fragmentPick, source: "pr_or_issue_body_contract_fragment", definition_kind: "contract" };
    }
    return { ok: false, reason: "ambiguous_definition_in_text", paths: validFromText };
  }

  const reviewPaths = [
    ...resolver.extractDefinitionPathsFromText(prBody),
    ...resolver.extractDefinitionPathsFromText(issueBody),
  ];
  const fromReviewText = pickContractDefinitionFromReviewPaths(reviewPaths, workspace);
  if (fromReviewText) {
    return { ok: true, path: fromReviewText, source: "review_definition_text", definition_kind: "contract" };
  }

  const fromChangedContract = pickContractDefinitionFromChangedFiles(changedFiles, branchInfo, workspace);
  if (fromChangedContract) {
    return {
      ok: true,
      path: fromChangedContract,
      source: "pr_changed_files_contract",
      definition_kind: "contract",
    };
  }

  const fromReviewChanged = pickContractDefinitionFromReviewChangedFiles(changedFiles, workspace, branchInfo);
  if (fromReviewChanged) {
    return {
      ok: true,
      path: fromReviewChanged,
      source: "pr_changed_files_review",
      definition_kind: "contract",
    };
  }

  return { ok: false, reason: "contract_definition_not_found" };
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

function preferContractSpecDefinitionPath(paths) {
  const list = [...new Set(paths || [])];
  if (list.length <= 1) return list[0] || "";
  const contractPaths = list.filter((candidate) =>
    /\/api-contract-spec\.ya?ml$/i.test(candidate),
  );
  if (contractPaths.length === 1) return contractPaths[0];
  return "";
}

function pickTaskDefinitionFromChangedFiles(changedFiles, branchInfo) {
  const taskFiles = (changedFiles || [])
    .map((entry) => (typeof entry === "string" ? entry : entry?.filename || ""))
    .filter((filename) => isTaskDefinitionPath(filename));

  if (taskFiles.length === 1) {
    return taskFiles[0];
  }

  const contractPick = preferContractSpecDefinitionPath(taskFiles);
  if (contractPick) return contractPick;

  if (branchInfo?.summary) {
    const summary = branchInfo.summary.toLowerCase();
    const summaryMatches = taskFiles.filter((filename) => {
      const lower = filename.toLowerCase();
      return lower.includes(`/${summary}/`) || lower.endsWith(`/${summary}.yaml`);
    });
    if (summaryMatches.length === 1) {
      return summaryMatches[0];
    }
    const contractFromSummary = preferContractSpecDefinitionPath(summaryMatches);
    if (contractFromSummary) return contractFromSummary;
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
  changedFiles = [],
}) {
  const workspace = nonEmpty(workspaceRoot) || process.cwd();
  const explicit = normalizePath(definitionOverride);
  if (explicit) {
    const absolute = path.join(workspace, explicit);
    if (!fileExists(absolute)) {
      return { ok: false, reason: "definition_override_missing", path: explicit };
    }
    const content = readFileSafe(absolute);
    const overrideKind = isHarnessDefinitionFile(explicit, content);
    if (!overrideKind) {
      return { ok: false, reason: "definition_override_not_task", path: explicit };
    }
    return { ok: true, path: explicit, source: "override", definition_kind: overrideKind };
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
  let resolvedIssueNumber = issueNumber || branchInfo?.issueNumber || null;
  if (
    branchInfo?.unit === "task" &&
    branchInfo.issueNumber > 0 &&
    issueNumber &&
    branchInfo.issueNumber !== issueNumber
  ) {
    resolvedIssueNumber = branchInfo.issueNumber;
  }

  if (branchInfo?.summary) {
    const fromSummary = resolver.findTaskDefinitionBySummary(workspace, branchInfo.summary);
    if (fromSummary.length === 1) {
      return { ok: true, path: fromSummary[0], source: "branch_summary" };
    }
    const contractFromSummary = preferContractSpecDefinitionPath(fromSummary);
    if (contractFromSummary) {
      return { ok: true, path: contractFromSummary, source: "branch_summary_contract_spec" };
    }
    if (fromSummary.length > 1) {
      return { ok: false, reason: "ambiguous_task_definition_by_summary", paths: fromSummary };
    }

    const fromFilename = findTaskDefinitionByFilenameSummary(workspace, branchInfo.summary);
    if (fromFilename.length === 1) {
      return { ok: true, path: fromFilename[0], source: "branch_summary_filename" };
    }
    const contractFromFilename = preferContractSpecDefinitionPath(fromFilename);
    if (contractFromFilename) {
      return { ok: true, path: contractFromFilename, source: "branch_summary_filename_contract_spec" };
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
  const contractFromScored = preferContractSpecDefinitionPath(scored.map((entry) => entry.path));
  if (contractFromScored) {
    return { ok: true, path: contractFromScored, source: "scan_contract_spec", definition_kind: "task" };
  }

  const branchInfoForChanged = resolver.parseBranchRef(headRef);
  const fromChangedTask = pickTaskDefinitionFromChangedFiles(changedFiles, branchInfoForChanged);
  if (fromChangedTask) {
    return { ok: true, path: fromChangedTask, source: "pr_changed_files", definition_kind: "task" };
  }

  const contractResolution = resolveContractDefinition({
    workspaceRoot: workspace,
    prBody,
    issueBody,
    headRef,
    changedFiles,
  });
  if (contractResolution.ok) {
    return contractResolution;
  }
  if (contractResolution.reason === "ambiguous_definition_in_text") {
    return contractResolution;
  }

  return {
    ok: false,
    reason: "task_definition_not_found",
    headRef,
    issueNumber: resolvedIssueNumber,
    hint:
      "PR 本文または Issue 本文に Task / Contract Definition パスを明示するか、--definition を指定してください。",
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
  extractContractDefinitionPathsFromText,
  hasTaskDefinitionType,
  hasContractDefinitionType,
  isTaskDefinitionPath,
  isContractDefinitionPath,
  pickTaskDefinitionFromChangedFiles,
  pickContractDefinitionFromChangedFiles,
  pickContractDefinitionFromReviewChangedFiles,
  resolveContractDefinition,
  findTaskDefinitionByFilenameSummary,
  listTaskDefinitionsByIssueNumber,
  resolveTaskDefinition,
};
