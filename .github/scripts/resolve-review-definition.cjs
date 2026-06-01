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

function extractDefinitionDirectoryHintsFromText(text) {
  const hints = new Set();
  const body = String(text || "");

  for (const match of body.matchAll(/`(prompts\/definitions\/[^`\s#]+)\/?`/g)) {
    hints.add(match[1].replace(/\/$/, ""));
  }

  for (const match of body.matchAll(/(?:Task \/ Review Definition|Review Definition)\s*:\s*`?(prompts\/definitions\/[^`\s#]+)\/?`?/gi)) {
    hints.add(match[1].replace(/\/$/, ""));
  }

  return [...hints];
}

function reviewDefinitionCandidatesFromDirectoryHints(directoryHints) {
  const paths = new Set();
  for (const dir of directoryHints) {
    const normalized = nonEmpty(dir).replace(/\\/g, "/").replace(/\/$/, "");
    if (!normalized.startsWith(DEFINITION_ROOT)) continue;
    paths.add(`${normalized}/${REVIEW_FILE_NAME}`);
  }
  return [...paths];
}

function pickReviewDefinitionFromChangedFiles(changedFiles, branchInfo) {
  const reviewFiles = (changedFiles || [])
    .map((entry) => (typeof entry === "string" ? entry : entry?.filename || ""))
    .filter((filename) => filename.startsWith(DEFINITION_ROOT) && filename.endsWith(`/${REVIEW_FILE_NAME}`));

  if (reviewFiles.length === 1) {
    return reviewFiles[0];
  }

  if (branchInfo?.summary) {
    const summaryMatches = reviewFiles.filter((filename) =>
      filename.toLowerCase().includes(`/${branchInfo.summary}/`),
    );
    if (summaryMatches.length === 1) {
      return summaryMatches[0];
    }
  }

  return "";
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
  const nestedValue = extractYamlScalar(scoped, "number");
  const nestedParsed = Number(nestedValue);
  if (Number.isInteger(nestedParsed) && nestedParsed > 0) {
    return nestedParsed;
  }
  const scalarMatch = /^\s*issue:\s*(\d+)\s*$/m.exec(block);
  if (scalarMatch) {
    const scalarParsed = Number(scalarMatch[1]);
    if (Number.isInteger(scalarParsed) && scalarParsed > 0) {
      return scalarParsed;
    }
  }
  return null;
}

function extractTargetPrNumber(reviewContent) {
  const targetBlock = /target:\s*[\s\S]*?(?=\n[a-z_]+:|\n\S|\s*$)/i.exec(String(reviewContent || ""));
  const block = targetBlock ? targetBlock[0] : reviewContent;
  const value = extractYamlScalar(block, "pr");
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function extractReviewType(reviewContent) {
  const reviewBlock = /review:\s*[\s\S]*?(?=\n[a-z_]+:|\n\S|\s*$)/i.exec(String(reviewContent || ""));
  const block = reviewBlock ? reviewBlock[0] : reviewContent;
  return extractYamlScalar(block, "type");
}

function epicReviewConventionPath(summary) {
  const normalized = nonEmpty(summary).toLowerCase();
  if (!normalized) return "";
  return `${DEFINITION_ROOT}reviews/${normalized}/epic/${REVIEW_FILE_NAME}`;
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

function scoreReviewCandidate(
  relativePath,
  { issueNumber, prNumber, branchInfo, taskDefinitionPath, workspaceRoot },
) {
  const absolute = path.join(workspaceRoot, relativePath);
  const content = readFileSafe(absolute);
  if (!content.includes('definition_type: "review"') && !content.includes("definition_type: review")) {
    return 0;
  }

  let score = 1;
  const targetIssue = extractTargetIssueNumber(content);
  const targetPr = extractTargetPrNumber(content);
  const linkedTask = extractTaskDefinitionPath(content);
  const reviewType = extractReviewType(content);

  if (issueNumber && targetIssue === issueNumber) score += 100;
  if (prNumber && targetPr === prNumber) score += 100;
  if (taskDefinitionPath && linkedTask === taskDefinitionPath) score += 100;

  if (branchInfo?.summary) {
    const summary = branchInfo.summary;
    if (branchInfo.unit === "epic") {
      const epicReviewPath = epicReviewConventionPath(summary);
      if (relativePath === epicReviewPath) score += 40;
      if (linkedTask.toLowerCase().includes(`/epics/${summary}/`)) score += 40;
      if (reviewType === "epic_pr_review") score += 30;
      if (reviewType === "task_pr_review") score -= 20;
    } else {
      if (relativePath.toLowerCase().includes(`/${summary}/`)) score += 40;
      if (linkedTask.toLowerCase().includes(`/${summary}/`) || linkedTask.toLowerCase().includes(`/${summary}.`)) {
        score += 40;
      }
      if (reviewType === "task_pr_review") score += 10;
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
  prNumber = null,
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
    ...reviewDefinitionCandidatesFromDirectoryHints([
      ...extractDefinitionDirectoryHintsFromText(prBody),
      ...extractDefinitionDirectoryHintsFromText(issueBody),
    ]),
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
  const resolvedPrNumber =
    Number.isInteger(Number(prNumber)) && Number(prNumber) > 0 ? Number(prNumber) : null;

  if (branchInfo?.unit === "epic" && branchInfo.summary) {
    const epicReviewPath = epicReviewConventionPath(branchInfo.summary);
    if (fileExists(path.join(workspace, epicReviewPath))) {
      return { ok: true, path: epicReviewPath, source: "epic_review_convention" };
    }
  }

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
        prNumber: resolvedPrNumber,
        branchInfo,
        taskDefinitionPath: [...taskCandidates][0] || "",
        workspaceRoot: workspace,
      }),
    }))
    .filter((entry) => entry.score > 0)
    .sort((a, b) => b.score - a.score);

  const strongMatches = scored.filter((entry) => entry.score >= 40);

  if (
    strongMatches.length === 1 ||
    (strongMatches.length > 1 && strongMatches[0].score > strongMatches[1].score)
  ) {
    return { ok: true, path: strongMatches[0].path, source: "scan", score: strongMatches[0].score };
  }
  if (strongMatches.length > 1 && strongMatches[0].score === strongMatches[1].score) {
    const hint =
      branchInfo?.unit === "epic" && branchInfo.summary
        ? `Epic Branch では ${epicReviewConventionPath(branchInfo.summary)} を作成するか、PR 本文に Review Definition パスを明示してください。`
        : undefined;
    return {
      ok: false,
      reason: "ambiguous_review_definition",
      paths: strongMatches.slice(0, 5).map((entry) => entry.path),
      hint,
    };
  }

  if (scored.length > 0) {
    const hint =
      branchInfo?.unit === "epic" && branchInfo.summary
        ? `Epic Branch では ${epicReviewConventionPath(branchInfo.summary)} を作成するか、PR 本文に Review Definition パスを明示してください。`
        : undefined;
    return {
      ok: false,
      reason: "review_definition_not_found",
      headRef,
      issueNumber: resolvedIssueNumber,
      hint,
      note: "Review Definition is not on the default branch. Resolve from PR head via changed files or explicit path.",
    };
  }

  return {
    ok: false,
    reason: "review_definition_not_found",
    headRef,
    issueNumber: resolvedIssueNumber,
    hint:
      branchInfo?.unit === "epic" && branchInfo.summary
        ? `Epic Branch では ${epicReviewConventionPath(branchInfo.summary)} を作成するか、PR 本文に Review Definition パスを明示してください。`
        : undefined,
  };
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
  extractDefinitionDirectoryHintsFromText,
  reviewDefinitionCandidatesFromDirectoryHints,
  pickReviewDefinitionFromChangedFiles,
  extractTaskDefinitionPath,
  extractTargetIssueNumber,
  extractTargetPrNumber,
  extractReviewType,
  epicReviewConventionPath,
  extractAiReviewRequired,
  listReviewDefinitionFiles,
  scoreReviewCandidate,
  resolveReviewDefinition,
  resolveAiReviewRequired,
  siblingReviewDefinitionForTask,
};
