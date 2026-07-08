"use strict";

const slack = require("./slack-notify.cjs");
const resolver = require("./resolve-review-definition.cjs");
const taskResolver = require("./resolve-task-definition.cjs");
const harness = require("./dispatch-definition-run.cjs");
const reviewAuto = require("./dispatch-review-pr-harness.cjs");
const requestIssueResolver = require("./resolve-harness-request-issue.cjs");

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

async function resolveTaskDefinitionForPull({
  workspaceRoot,
  pull,
  issueBody,
  issueNumber,
  definitionOverride,
  changedFiles,
}) {
  const headRef = pull.head?.ref || "";
  return taskResolver.resolveTaskDefinition({
    workspaceRoot,
    prBody: pull.body || "",
    issueBody,
    headRef,
    issueNumber,
    definitionOverride,
    changedFiles,
  });
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
    'gh workflow run "Definition Run Harness"',
    `-f command=fix-review-comments`,
    `-f definition=${definition || "prompts/definitions/tasks/.../task.yaml"}`,
    "-f run_mode=live-run",
    `-f target_pr=${prNumber}`,
  ];
  if (issueNumber) parts.push(`-f request_issue=${issueNumber}`);
  if (headRef) parts.push(`-f ref=${headRef}`);
  parts.push(`--repo ${owner}/${repo}`);
  return parts.join(" \\\n  ");
}

function buildRecoveryCommand({ owner, repo, prNumber, definition, issueNumber, requestedBy, context }) {
  const parts = [
    "node .github/scripts/dispatch-fix-review-harness.cjs",
    `--repository ${owner}/${repo}`,
    `--pr ${prNumber}`,
  ];
  if (definition) parts.push(`--definition ${definition}`);
  if (issueNumber) parts.push(`--issue ${issueNumber}`);
  if (requestedBy) parts.push(`--requested-by ${requestedBy}`);
  if (context) parts.push(`--context ${context}`);
  return parts.join(" \\\n  ");
}

async function dispatchFixReviewHarness({
  owner,
  repo,
  repository,
  prNumber,
  issueNumber,
  definition,
  requestedBy,
  context,
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

  const workspaceEarly = nonEmpty(workspaceRoot) || process.cwd();
  let relatedIssue =
    requestIssueResolver.resolveHarnessRequestIssue({
      workspaceRoot: workspaceEarly,
      pull,
      issueNumberArg: issueNumber,
      reviewDefinitionPath: definition,
    }) || null;

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
  const dispatchContext = nonEmpty(context);
  if (reviewAuto.isHarnessAutoDispatchContext(dispatchContext)) {
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

  const headRef = pull.head?.ref || "";

  const fixerSkip = reviewAuto.shouldSkipFixerHarnessAutoDispatch({
    context: dispatchContext,
    pullLabels,
    issueLabels,
    changedFiles,
    headRef,
  });
  if (fixerSkip.skip) {
    return {
      ok: true,
      skipped: true,
      reason: fixerSkip.reason,
      pr_number: String(pr),
      issue_number: relatedIssue ? String(relatedIssue) : null,
    };
  }

  const workspace = nonEmpty(workspaceRoot) || process.cwd();
  const taskResolution = await resolveTaskDefinitionForPull({
    workspaceRoot: workspace,
    pull,
    issueBody,
    issueNumber: relatedIssue,
    definitionOverride: definition,
    changedFiles,
  });

  if (!taskResolution.ok) {
    return {
      ok: false,
      reason: taskResolution.reason,
      pr_number: String(pr),
      issue_number: relatedIssue ? String(relatedIssue) : null,
      details: taskResolution,
      recovery_command: buildRecoveryCommand({
        owner: resolvedRepo.owner,
        repo: resolvedRepo.repo,
        prNumber: pr,
        definition: definition || "",
        issueNumber: relatedIssue,
        requestedBy,
        context: dispatchContext || "request-changes",
      }),
    };
  }

  const reviewFromTask = resolver.resolveReviewDefinitionFromTaskPath(
    taskResolution.path,
    workspace,
  );
  relatedIssue =
    requestIssueResolver.resolveHarnessRequestIssue({
      workspaceRoot: workspace,
      pull,
      issueNumberArg: issueNumber,
      reviewDefinitionPath: reviewFromTask.ok ? reviewFromTask.path : "",
    }) || relatedIssue;

  const dispatchResult = await harness.dispatchDefinitionRun({
    owner: resolvedRepo.owner,
    repo: resolvedRepo.repo,
    command: "fix-review-comments",
    definition: taskResolution.path,
    runMode: "live-run",
    targetPr: String(pr),
    requestIssue: relatedIssue ? String(relatedIssue) : "",
    requestedBy: nonEmpty(requestedBy) || nonEmpty(context) || "fixer-auto-dispatch",
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
    task_definition: taskResolution.path,
    task_definition_source: taskResolution.source,
    harness_ref: headRef || null,
    dispatch: dispatchResult,
    recovery_command: buildRecoveryCommand({
      owner: resolvedRepo.owner,
      repo: resolvedRepo.repo,
      prNumber: pr,
      definition: taskResolution.path,
      issueNumber: relatedIssue,
      requestedBy: "manual-recovery",
      context: "request-changes",
    }),
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
  node .github/scripts/dispatch-fix-review-harness.cjs \\
    --repository owner/repo \\
    --pr <number> \\
    [--definition prompts/definitions/tasks/.../task.yaml] \\
    [--issue <number>] [--requested-by <id>] \\
    [--context request-changes] \\
    [--workspace <path>] [--dry-run]

Resolves Task Definition and dispatches Definition Run Harness (fix-review-comments live-run).
`);
}

async function main() {
  const options = parseCliArgs(process.argv);
  if (options.help) {
    printHelp();
    return;
  }
  const result = await dispatchFixReviewHarness({
    owner: options.owner,
    repo: options.repo,
    repository: options.repository,
    prNumber: options.prNumber,
    issueNumber: options.issueNumber,
    definition: options.definition,
    requestedBy: options.requestedBy,
    context: options.context,
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
  buildHarnessDirectRecoveryCommand,
  buildRecoveryCommand,
  dispatchFixReviewHarness,
  resolveTaskDefinitionForPull,
};
