"use strict";

const slack = require("./slack-notify.cjs");
const resolver = require("./resolve-review-definition.cjs");
const harness = require("./dispatch-definition-run.cjs");

function nonEmpty(value) {
  return String(value || "").trim();
}

function resolveRepository({ owner, repo, repository }) {
  if (owner && repo) return { owner: nonEmpty(owner), repo: nonEmpty(repo) };
  const full = nonEmpty(repository) || nonEmpty(process.env.GITHUB_REPOSITORY);
  if (!full || !full.includes("/")) {
    throw new Error("repository is required (--owner/--repo or GITHUB_REPOSITORY)");
  }
  const [resolvedOwner, resolvedRepo] = full.split("/", 2);
  return { owner: resolvedOwner, repo: resolvedRepo };
}

function authHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
  };
}

async function fetchJson(url, token, fetchImpl) {
  const send = fetchImpl || global.fetch;
  const response = await send(url, { headers: authHeaders(token) });
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`GitHub API failed: HTTP ${response.status} ${text}`.trim());
  }
  return response.json();
}

async function loadPullRequestFiles({ owner, repo, prNumber, token, fetchImpl }) {
  const files = [];
  let page = 1;
  const send = fetchImpl || global.fetch;

  for (;;) {
    const url = `https://api.github.com/repos/${owner}/${repo}/pulls/${prNumber}/files?per_page=100&page=${page}`;
    const response = await send(url, { headers: authHeaders(token) });
    if (!response.ok) {
      const text = await response.text().catch(() => "");
      throw new Error(`GitHub API failed: HTTP ${response.status} ${text}`.trim());
    }
    const batch = await response.json();
    if (!Array.isArray(batch) || batch.length === 0) break;
    files.push(...batch);
    if (batch.length < 100) break;
    page += 1;
  }

  return files;
}

async function resolveReviewDefinitionForPull({
  workspaceRoot,
  pull,
  issueBody,
  issueNumber,
  definitionOverride,
  owner,
  repo,
  token,
  fetchImpl,
}) {
  const headRef = pull.head?.ref || "";
  const branchInfo = resolver.parseBranchRef(headRef);
  let reviewResolution = resolver.resolveReviewDefinition({
    workspaceRoot,
    prBody: pull.body || "",
    issueBody,
    headRef,
    issueNumber,
    definitionOverride,
  });

  if (reviewResolution.ok) {
    return reviewResolution;
  }

  const shouldFallback =
    reviewResolution.reason === "ambiguous_review_definition" ||
    reviewResolution.reason === "review_definition_not_found" ||
    reviewResolution.reason === "ambiguous_definition_in_text";

  if (!shouldFallback) {
    return reviewResolution;
  }

  const fromPrFiles = resolver.pickReviewDefinitionFromChangedFiles(
    await loadPullRequestFiles({ owner, repo, prNumber: pull.number, token, fetchImpl }),
    branchInfo,
  );
  if (fromPrFiles) {
    return { ok: true, path: fromPrFiles, source: "pr_changed_files" };
  }

  const directoryCandidates = resolver.reviewDefinitionCandidatesFromDirectoryHints([
    ...resolver.extractDefinitionDirectoryHintsFromText(pull.body || ""),
    ...resolver.extractDefinitionDirectoryHintsFromText(issueBody),
  ]);
  if (branchInfo?.summary) {
    directoryCandidates.push(`${resolver.DEFINITION_ROOT}_e2e/${branchInfo.summary}/${resolver.REVIEW_FILE_NAME}`);
  }

  const uniqueCandidates = [...new Set(directoryCandidates)];
  if (uniqueCandidates.length === 1) {
    return { ok: true, path: uniqueCandidates[0], source: "pr_body_directory_hint" };
  }

  return reviewResolution;
}

async function loadPullRequest({ owner, repo, prNumber, token, fetchImpl }) {
  return fetchJson(
    `https://api.github.com/repos/${owner}/${repo}/pulls/${prNumber}`,
    token,
    fetchImpl,
  );
}

async function loadIssue({ owner, repo, issueNumber, token, fetchImpl }) {
  return fetchJson(
    `https://api.github.com/repos/${owner}/${repo}/issues/${issueNumber}`,
    token,
    fetchImpl,
  );
}

function shouldSkipForContext({ context, fixOutcome }) {
  const ctx = nonEmpty(context);
  if (ctx === "fix-ready") {
    const normalized = slack.normalizeKnownFixOutcome(fixOutcome) || "ready_for_ai_review";
    return normalized !== "ready_for_ai_review"
      ? { skip: true, reason: "fix_outcome_not_ready_for_ai_review", fix_outcome: normalized }
      : { skip: false };
  }
  return { skip: false };
}

const HARNESS_AUTO_DISPATCH_CONTEXTS = Object.freeze(["pr-created", "fix-ready"]);

const INFRA_HARNESS_SKIP_LABELS = Object.freeze([
  "type: infra",
  "type:infra",
  "area: infra",
  "area:infra",
]);

const AUTOMATION_ONLY_CHANGED_FILE_PREFIXES = Object.freeze([".github/"]);

function normalizeLabelNames(labels) {
  return (labels || []).map((item) => String(item.name || item).trim().toLowerCase()).filter(Boolean);
}

function hasInfraHarnessSkipLabel(labels) {
  const names = normalizeLabelNames(labels);
  return names.some((name) => INFRA_HARNESS_SKIP_LABELS.includes(name));
}

function changedFilesAreAutomationOnly(files) {
  const paths = (files || [])
    .map((item) => String(item.filename || item.path || item).trim())
    .filter(Boolean);
  if (!paths.length) return false;
  return paths.every((filePath) =>
    AUTOMATION_ONLY_CHANGED_FILE_PREFIXES.some((prefix) => filePath.startsWith(prefix)),
  );
}

function isHarnessAutoDispatchContext(context) {
  return HARNESS_AUTO_DISPATCH_CONTEXTS.includes(nonEmpty(context));
}

function shouldSkipHarnessAutoDispatch({ context, pullLabels, issueLabels, changedFiles }) {
  if (!isHarnessAutoDispatchContext(context)) {
    return { skip: false };
  }

  if (hasInfraHarnessSkipLabel(pullLabels) || hasInfraHarnessSkipLabel(issueLabels)) {
    return { skip: true, reason: "infra_pr" };
  }

  if (changedFilesAreAutomationOnly(changedFiles)) {
    return { skip: true, reason: "automation_only_changes" };
  }

  return { skip: false };
}

function buildHarnessDirectRecoveryCommand({
  owner,
  repo,
  prNumber,
  definition,
  issueNumber,
  headRef,
}) {
  const parts = [
    "gh workflow run \"Definition Run Harness\"",
    `-f command=review-pr`,
    `-f definition=${definition || "prompts/definitions/<path>/pr-review.yaml"}`,
    "-f run_mode=live-run",
    `-f target_pr=${prNumber}`,
  ];
  if (issueNumber) parts.push(`-f request_issue=${issueNumber}`);
  if (headRef) parts.push(`-f ref=${headRef}`);
  parts.push(`--repo ${owner}/${repo}`);
  return parts.join(" \\\n  ");
}

function buildRecoveryCommand({ owner, repo, prNumber, definition, issueNumber, requestedBy }) {
  const parts = [
    "node .github/scripts/dispatch-review-pr-harness.cjs",
    `--repository ${owner}/${repo}`,
    `--pr ${prNumber}`,
  ];
  if (definition) parts.push(`--definition ${definition}`);
  if (issueNumber) parts.push(`--issue ${issueNumber}`);
  if (requestedBy) parts.push(`--requested-by ${requestedBy}`);
  return parts.join(" \\\n  ");
}

async function dispatchReviewPrHarness({
  owner,
  repo,
  repository,
  prNumber,
  issueNumber,
  definition,
  requestedBy,
  context,
  fixOutcome,
  workspaceRoot,
  token,
  dryRun,
  fetchImpl,
}) {
  const resolvedRepo = resolveRepository({ owner, repo, repository });
  const authToken = nonEmpty(token) || nonEmpty(process.env.GITHUB_TOKEN) || nonEmpty(process.env.GH_TOKEN);
  if (!authToken) {
    throw new Error("GITHUB_TOKEN or GH_TOKEN is required");
  }

  const contextGate = shouldSkipForContext({ context, fixOutcome });
  if (contextGate.skip) {
    return { ok: true, skipped: true, ...contextGate };
  }

  const pr = Number(prNumber);
  if (!Number.isInteger(pr) || pr <= 0) {
    throw new Error(`Invalid pr_number: ${prNumber}`);
  }

  const pull = await loadPullRequest({
    owner: resolvedRepo.owner,
    repo: resolvedRepo.repo,
    prNumber: pr,
    token: authToken,
    fetchImpl,
  });

  const repositoryFullName = `${resolvedRepo.owner}/${resolvedRepo.repo}`;
  if (pull.head?.repo?.full_name !== repositoryFullName) {
    return { ok: true, skipped: true, reason: "fork_pr" };
  }

  const relatedIssue =
    Number(issueNumber) ||
    Number(slack.relatedIssueNumber(pull.body || "")) ||
    resolver.parseBranchRef(pull.head?.ref || "")?.issueNumber ||
    null;

  let issueBody = "";
  let issueLabels = [];
  if (relatedIssue) {
    const issue = await loadIssue({
      owner: resolvedRepo.owner,
      repo: resolvedRepo.repo,
      issueNumber: relatedIssue,
      token: authToken,
      fetchImpl,
    });
    issueBody = issue.body || "";
    issueLabels = issue.labels || [];
  }

  let pullLabels = pull.labels || [];
  let changedFiles = [];
  if (isHarnessAutoDispatchContext(context)) {
    if (!pullLabels.length) {
      const pullIssue = await loadIssue({
        owner: resolvedRepo.owner,
        repo: resolvedRepo.repo,
        issueNumber: pr,
        token: authToken,
        fetchImpl,
      });
      pullLabels = pullIssue.labels || [];
    }
    changedFiles = await loadPullRequestFiles({
      owner: resolvedRepo.owner,
      repo: resolvedRepo.repo,
      prNumber: pr,
      token: authToken,
      fetchImpl,
    });
  }

  const infraSkip = shouldSkipHarnessAutoDispatch({
    context,
    pullLabels,
    issueLabels,
    changedFiles,
  });
  if (infraSkip.skip) {
    return {
      ok: true,
      skipped: true,
      reason: infraSkip.reason,
      pr_number: String(pr),
      issue_number: relatedIssue ? String(relatedIssue) : null,
    };
  }

  const workspace = nonEmpty(workspaceRoot) || process.cwd();
  const headRef = pull.head?.ref || "";
  const reviewResolution = await resolveReviewDefinitionForPull({
    workspaceRoot: workspace,
    pull,
    issueBody,
    issueNumber: relatedIssue,
    definitionOverride: definition,
    owner: resolvedRepo.owner,
    repo: resolvedRepo.repo,
    token: authToken,
    fetchImpl,
  });

  if (!reviewResolution.ok) {
    return {
      ok: false,
      reason: reviewResolution.reason,
      pr_number: String(pr),
      issue_number: relatedIssue ? String(relatedIssue) : null,
      details: reviewResolution,
      recovery_command: buildRecoveryCommand({
        owner: resolvedRepo.owner,
        repo: resolvedRepo.repo,
        prNumber: pr,
        issueNumber: relatedIssue,
        requestedBy,
      }),
    };
  }

  const aiReviewGate = resolver.resolveAiReviewRequired({
    workspaceRoot: workspace,
    reviewDefinitionPath: reviewResolution.path,
  });
  const skipAiReview =
    aiReviewGate.ok &&
    aiReviewGate.required === false &&
    aiReviewGate.source === "task_definition";
  if (skipAiReview) {
    return {
      ok: true,
      skipped: true,
      reason: "ai_review_not_required",
      review_definition: reviewResolution.path,
      task_definition: aiReviewGate.task_definition || null,
    };
  }

  const dispatchResult = await harness.dispatchDefinitionRun({
    owner: resolvedRepo.owner,
    repo: resolvedRepo.repo,
    command: "review-pr",
    definition: reviewResolution.path,
    runMode: "live-run",
    targetPr: String(pr),
    requestIssue: relatedIssue ? String(relatedIssue) : "",
    requestedBy: nonEmpty(requestedBy) || nonEmpty(context) || "ai-review-auto-dispatch",
    workspaceRoot: workspace,
    ref: headRef,
    token: authToken,
    dryRun,
    fetchImpl,
  });

  return {
    ok: true,
    pr_number: String(pr),
    issue_number: relatedIssue ? String(relatedIssue) : null,
    review_definition: reviewResolution.path,
    review_definition_source: reviewResolution.source,
    harness_ref: headRef || null,
    ai_review_required: true,
    dispatch: dispatchResult,
  };
}

function parseCliArgs(argv) {
  const args = argv.slice(2);
  const options = {
    owner: "",
    repo: "",
    repository: "",
    prNumber: "",
    issueNumber: "",
    definition: "",
    requestedBy: "",
    context: "",
    fixOutcome: "",
    workspaceRoot: "",
    dryRun: false,
  };
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--dry-run") {
      options.dryRun = true;
      continue;
    }
    if (arg === "--owner") {
      options.owner = args[++i] || "";
      continue;
    }
    if (arg === "--repo") {
      options.repo = args[++i] || "";
      continue;
    }
    if (arg === "--repository" || arg === "-R") {
      options.repository = args[++i] || "";
      continue;
    }
    if (arg === "--pr" || arg === "--pr-number") {
      options.prNumber = args[++i] || "";
      continue;
    }
    if (arg === "--issue" || arg === "--request-issue") {
      options.issueNumber = args[++i] || "";
      continue;
    }
    if (arg === "--definition") {
      options.definition = args[++i] || "";
      continue;
    }
    if (arg === "--requested-by") {
      options.requestedBy = args[++i] || "";
      continue;
    }
    if (arg === "--context") {
      options.context = args[++i] || "";
      continue;
    }
    if (arg === "--fix-outcome") {
      options.fixOutcome = args[++i] || "";
      continue;
    }
    if (arg === "--workspace") {
      options.workspaceRoot = args[++i] || "";
      continue;
    }
    if (arg === "--help" || arg === "-h") {
      options.help = true;
      continue;
    }
    throw new Error(`Unknown argument: ${arg}`);
  }
  return options;
}

function printHelp() {
  process.stdout.write(`Usage:
  node .github/scripts/dispatch-review-pr-harness.cjs \\
    --repository owner/repo \\
    --pr <number> \\
    [--definition prompts/definitions/.../pr-review.yaml] \\
    [--issue <number>] [--requested-by <id>] \\
    [--context pr-created|fix-ready] [--fix-outcome ready_for_ai_review] \\
    [--workspace <path>] [--dry-run]

Resolves Review Definition and dispatches Definition Run Harness (review-pr live-run).
`);
}

async function main() {
  const options = parseCliArgs(process.argv);
  if (options.help) {
    printHelp();
    return;
  }
  const result = await dispatchReviewPrHarness({
    owner: options.owner,
    repo: options.repo,
    repository: options.repository,
    prNumber: options.prNumber,
    issueNumber: options.issueNumber,
    definition: options.definition,
    requestedBy: options.requestedBy,
    context: options.context,
    fixOutcome: options.fixOutcome,
    workspaceRoot: options.workspaceRoot,
    dryRun: options.dryRun,
  });
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  if (result.ok === false) process.exitCode = 1;
}

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = {
  AUTOMATION_ONLY_CHANGED_FILE_PREFIXES,
  HARNESS_AUTO_DISPATCH_CONTEXTS,
  INFRA_HARNESS_SKIP_LABELS,
  buildHarnessDirectRecoveryCommand,
  buildRecoveryCommand,
  changedFilesAreAutomationOnly,
  dispatchReviewPrHarness,
  hasInfraHarnessSkipLabel,
  isHarnessAutoDispatchContext,
  shouldSkipForContext,
  shouldSkipHarnessAutoDispatch,
};
