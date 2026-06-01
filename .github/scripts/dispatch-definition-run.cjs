"use strict";

const builder = require("./definition-run-prompt-builder.cjs");

const EVENT_TYPE = "definition-run";

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

function buildClientPayload({
  command,
  definition,
  runMode,
  targetPr,
  requestIssue,
  requestedBy,
  workspaceRoot,
  ref,
}) {
  const cmd = nonEmpty(command) || "review-pr";
  const def = nonEmpty(definition);
  const mode = nonEmpty(runMode) || "live-run";
  if (!def) throw new Error("definition is required");
  if (!def.startsWith(builder.DEFINITION_PATH_PREFIX)) {
    throw new Error(`definition must start with ${builder.DEFINITION_PATH_PREFIX}`);
  }

  builder.buildDefinitionRunRequest(
    {
      command: cmd,
      definition: def,
      run_mode: mode,
      target_pr: nonEmpty(targetPr),
      request_issue: nonEmpty(requestIssue),
      requested_by: nonEmpty(requestedBy),
      ref: nonEmpty(ref),
    },
    { workspace: nonEmpty(workspaceRoot) || process.cwd() },
  );

  const payload = {
    command: cmd,
    definition: def,
    run_mode: mode,
  };
  const pr = nonEmpty(targetPr);
  if (pr) payload.target_pr = pr;
  const issue = nonEmpty(requestIssue);
  if (issue) payload.request_issue = issue;
  const by = nonEmpty(requestedBy);
  if (by) payload.requested_by = by;
  const branchRef = nonEmpty(ref);
  if (branchRef) payload.ref = branchRef;
  return payload;
}

function dispatchUrl(owner, repo) {
  return `https://api.github.com/repos/${owner}/${repo}/dispatches`;
}

async function dispatchDefinitionRun({
  owner,
  repo,
  repository,
  command,
  definition,
  runMode,
  targetPr,
  requestIssue,
  requestedBy,
  workspaceRoot,
  ref,
  token,
  dryRun,
  fetchImpl,
}) {
  const resolved = resolveRepository({ owner, repo, repository });
  const authToken = nonEmpty(token) || nonEmpty(process.env.GITHUB_TOKEN) || nonEmpty(process.env.GH_TOKEN);
  if (!authToken) {
    throw new Error("GITHUB_TOKEN or GH_TOKEN is required to dispatch repository_dispatch");
  }
  const workspace = nonEmpty(workspaceRoot) || process.cwd();
  const clientPayload = buildClientPayload({
    command,
    definition,
    runMode,
    targetPr,
    requestIssue,
    requestedBy,
    workspaceRoot: workspace,
    ref,
  });

  if (dryRun) {
    return {
      ok: true,
      dryRun: true,
      eventType: EVENT_TYPE,
      owner: resolved.owner,
      repo: resolved.repo,
      clientPayload,
    };
  }

  const send = fetchImpl || global.fetch;
  if (typeof send !== "function") {
    throw new Error("fetch is unavailable");
  }

  const response = await send(dispatchUrl(resolved.owner, resolved.repo), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${authToken}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify({
      event_type: EVENT_TYPE,
      client_payload: clientPayload,
    }),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`repository_dispatch failed: HTTP ${response.status} ${text}`.trim());
  }

  return {
    ok: true,
    eventType: EVENT_TYPE,
    owner: resolved.owner,
    repo: resolved.repo,
    clientPayload,
  };
}

function parseCliArgs(argv) {
  const args = argv.slice(2);
  const options = {
    owner: "",
    repo: "",
    repository: "",
    command: "review-pr",
    definition: "",
    runMode: "live-run",
    targetPr: "",
    requestIssue: "",
    requestedBy: "",
    ref: "",
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
    if (arg === "--command") {
      options.command = args[++i] || "";
      continue;
    }
    if (arg === "--definition") {
      options.definition = args[++i] || "";
      continue;
    }
    if (arg === "--run-mode") {
      options.runMode = args[++i] || "";
      continue;
    }
    if (arg === "--target-pr" || arg === "--pr") {
      options.targetPr = args[++i] || "";
      continue;
    }
    if (arg === "--request-issue" || arg === "--issue") {
      options.requestIssue = args[++i] || "";
      continue;
    }
    if (arg === "--requested-by") {
      options.requestedBy = args[++i] || "";
      continue;
    }
    if (arg === "--ref") {
      options.ref = args[++i] || "";
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
  node .github/scripts/dispatch-definition-run.cjs \\
    --definition prompts/definitions/.../pr-review.yaml \\
    --target-pr <number> \\
    [--command review-pr] [--run-mode live-run] \\
    [--request-issue <number>] [--requested-by <id>] \\
    [--ref <git-ref>] [--repository owner/repo] [--dry-run]

Dispatches repository event "${EVENT_TYPE}" to run Definition Run Harness.
`);
}

async function main() {
  const options = parseCliArgs(process.argv);
  if (options.help) {
    printHelp();
    return;
  }
  const result = await dispatchDefinitionRun(options);
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = {
  EVENT_TYPE,
  buildClientPayload,
  dispatchDefinitionRun,
};
