"use strict";

const fs = require("node:fs");
const path = require("node:path");

const DEFINITION_ROOT = "prompts/definitions/";
const REVIEW_FILE_NAME = "pr-review.yaml";

function nonEmpty(value) {
  return String(value || "").trim();
}

function normalizePath(value) {
  const raw = nonEmpty(value).replace(/\\/g, "/");
  if (!raw) return "";
  return raw.startsWith(DEFINITION_ROOT) ? raw : "";
}

function parseBranchRef(headRef) {
  const ref = nonEmpty(headRef);
  const match = /(?:^|\/)(epic|task)-(\d+)-([a-z0-9-]+)$/i.exec(ref);
  if (!match) return null;
  return {
    unit: match[1].toLowerCase(),
    issueNumber: Number(match[2]),
    summary: match[3].toLowerCase(),
  };
}

function extractDefinitionPathsFromText(text) {
  const paths = new Set();
  const body = String(text || "");

  for (const match of body.matchAll(/\/review-pr\s+@([^\s#`]+)/gi)) {
    const candidate = normalizePath(match[1]);
    if (candidate) paths.add(candidate);
  }

  for (const match of body.matchAll(
    /(?:Review Definition|review_definition|ReviewDefinition)\s*[:：]\s*`?([^\s`#]+\.ya?ml)`?/gi,
  )) {
    const candidate = normalizePath(match[1]);
    if (candidate) paths.add(candidate);
  }

  return [...paths];
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

function extractYamlScalar(content, key) {
  const pattern = new RegExp(`^\\s*${key}:\\s*"?([^"\\n#]+)"?`, "m");
  const match = pattern.exec(String(content || ""));
  return match ? nonEmpty(match[1]) : "";
}

function extractTaskDefinitionPath(reviewContent) {
  const targetBlock = /target:\s*[\s\S]*?(?=\n[a-z_]+:|\n\S|\s*$)/i.exec(String(reviewContent || ""));
  const block = targetBlock ? targetBlock[0] : reviewContent;
  return normalizePath(extractYamlScalar(block, "task_definition"));
}

function extractTargetIssueNumber(reviewContent) {
  const issueBlock = /target:\s*[\s\S]*?(?=\n[a-z_]+:|\n\S|\s*$)/i.exec(String(reviewContent || ""));
  const block = issueBlock ? issueBlock[0] : reviewContent;
  const issueSection = /issue:\s*[\s\S]*?(?=\n\s{0,2}[a-z_]+:|\s*$)/i.exec(block);
  const scoped = issueSection ? issueSection[0] : block;
  const value = extractYamlScalar(scoped, "number");
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function extractAiReviewRequired(taskContent) {
  const reviewBlock = /review:\s*[\s\S]*?(?=\n[a-z_]+:|\n\S|\s*$)/i.exec(String(taskContent || ""));
  const block = reviewBlock ? reviewBlock[0] : taskContent;
  const value = extractYamlScalar(block, "ai_review_required").toLowerCase();
  if (value === "false") return false;
  if (value === "true") return true;
  return true;
}

function listReviewDefinitionFiles(workspaceRoot) {
  const root = path.join(workspaceRoot, DEFINITION_ROOT);
  const results = [];

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
      if (entry.isFile() && entry.name === REVIEW_FILE_NAME) {
        results.push(full);
      }
    }
  }

  walk(root);
  return results.map((absolute) => absolute.replace(/\\/g, "/").slice(workspaceRoot.replace(/\\/g, "/").length + 1));
}

function siblingReviewDefinitionForTask(taskDefinitionPath, workspaceRoot) {
  const taskPath = normalizePath(taskDefinitionPath);
  if (!taskPath) return "";
  const absoluteTask = path.join(workspaceRoot, taskPath);
  const sibling = path.join(path.dirname(absoluteTask), REVIEW_FILE_NAME);
  if (!fileExists(sibling)) return "";
  return sibling.replace(/\\/g, "/").slice(workspaceRoot.replace(/\\/g, "/").length + 1);
}

function findTaskDefinitionBySummary(workspaceRoot, summary) {
  const matches = [];
  const root = path.join(workspaceRoot, DEFINITION_ROOT);

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
        if (entry.name.toLowerCase() === summary) {
          for (const candidate of ["task.yaml", `${summary}.yaml`]) {
            const taskFile = path.join(full, candidate);
            if (fileExists(taskFile)) {
              matches.push(
                taskFile.replace(/\\/g, "/").slice(workspaceRoot.replace(/\\/g, "/").length + 1),
              );
            }
          }
        }
        walk(full);
      }
    }
  }

  walk(root);
  return matches;
}

function scoreReviewCandidate(relativePath, { issueNumber, branchInfo, taskDefinitionPath, workspaceRoot }) {
  const absolute = path.join(workspaceRoot, relativePath);
  const content = readFileSafe(absolute);
  if (!content.includes('definition_type: "review"') && !content.includes("definition_type: review")) {
    return 0;
  }

  let score = 1;
  const targetIssue = extractTargetIssueNumber(content);
  const linkedTask = extractTaskDefinitionPath(content);

  if (issueNumber && targetIssue === issueNumber) score += 100;
  if (taskDefinitionPath && linkedTask === taskDefinitionPath) score += 100;

  if (branchInfo?.summary) {
    const summary = branchInfo.summary;
    if (relativePath.toLowerCase().includes(`/${summary}/`)) score += 40;
    if (linkedTask.toLowerCase().includes(`/${summary}/`) || linkedTask.toLowerCase().includes(`/${summary}.`)) {
      score += 40;
    }
  }

  return score;
}

function resolveReviewDefinition({
  workspaceRoot,
  prBody = "",
  issueBody = "",
  headRef = "",
  issueNumber = null,
  definitionOverride = "",
  taskDefinitionOverride = "",
}) {
  const workspace = nonEmpty(workspaceRoot) || process.cwd();
  const explicit = normalizePath(definitionOverride);
  if (explicit) {
    const absolute = path.join(workspace, explicit);
    if (!fileExists(absolute)) {
      return { ok: false, reason: "definition_override_missing", path: explicit };
    }
    return { ok: true, path: explicit, source: "override" };
  }

  const fromText = [
    ...extractDefinitionPathsFromText(prBody),
    ...extractDefinitionPathsFromText(issueBody),
  ];
  const validFromText = fromText.filter((candidate) => fileExists(path.join(workspace, candidate)));
  if (validFromText.length === 1) {
    return { ok: true, path: validFromText[0], source: "pr_or_issue_body" };
  }
  if (validFromText.length > 1) {
    return { ok: false, reason: "ambiguous_definition_in_text", paths: validFromText };
  }

  const branchInfo = parseBranchRef(headRef);
  const resolvedIssueNumber = issueNumber || branchInfo?.issueNumber || null;

  const taskOverride = normalizePath(taskDefinitionOverride);
  const taskCandidates = new Set();
  if (taskOverride && fileExists(path.join(workspace, taskOverride))) {
    taskCandidates.add(taskOverride);
  }
  if (branchInfo?.summary) {
    for (const taskPath of findTaskDefinitionBySummary(workspace, branchInfo.summary)) {
      taskCandidates.add(taskPath);
    }
    const e2eReview = `${DEFINITION_ROOT}_e2e/${branchInfo.summary}/${REVIEW_FILE_NAME}`;
    if (fileExists(path.join(workspace, e2eReview))) {
      return { ok: true, path: e2eReview, source: "e2e_branch_summary" };
    }
  }

  for (const taskPath of taskCandidates) {
    const sibling = siblingReviewDefinitionForTask(taskPath, workspace);
    if (sibling) {
      return { ok: true, path: sibling, source: "task_sibling", task_definition: taskPath };
    }
  }

  const scored = listReviewDefinitionFiles(workspace)
    .map((relativePath) => ({
      path: relativePath,
      score: scoreReviewCandidate(relativePath, {
        issueNumber: resolvedIssueNumber,
        branchInfo,
        taskDefinitionPath: [...taskCandidates][0] || "",
        workspaceRoot: workspace,
      }),
    }))
    .filter((entry) => entry.score > 0)
    .sort((a, b) => b.score - a.score);

  if (scored.length === 1 || (scored.length > 1 && scored[0].score > scored[1].score)) {
    return { ok: true, path: scored[0].path, source: "scan", score: scored[0].score };
  }
  if (scored.length > 1 && scored[0].score === scored[1].score) {
    return {
      ok: false,
      reason: "ambiguous_review_definition",
      paths: scored.slice(0, 5).map((entry) => entry.path),
    };
  }

  return { ok: false, reason: "review_definition_not_found", headRef, issueNumber: resolvedIssueNumber };
}

function resolveAiReviewRequired({ workspaceRoot, reviewDefinitionPath, taskDefinitionPath = "" }) {
  const workspace = nonEmpty(workspaceRoot) || process.cwd();
  const reviewAbsolute = path.join(workspace, reviewDefinitionPath);
  const reviewContent = readFileSafe(reviewAbsolute);
  const linkedTask = normalizePath(taskDefinitionPath) || extractTaskDefinitionPath(reviewContent);
  if (!linkedTask) return { ok: true, required: true, source: "default" };

  const taskAbsolute = path.join(workspace, linkedTask);
  if (!fileExists(taskAbsolute)) return { ok: true, required: true, source: "task_missing_default_true" };

  const taskContent = readFileSafe(taskAbsolute);
  return {
    ok: true,
    required: extractAiReviewRequired(taskContent),
    source: "task_definition",
    task_definition: linkedTask,
  };
}

module.exports = {
  DEFINITION_ROOT,
  REVIEW_FILE_NAME,
  parseBranchRef,
  extractDefinitionPathsFromText,
  extractTaskDefinitionPath,
  extractAiReviewRequired,
  listReviewDefinitionFiles,
  resolveReviewDefinition,
  resolveAiReviewRequired,
  siblingReviewDefinitionForTask,
};
