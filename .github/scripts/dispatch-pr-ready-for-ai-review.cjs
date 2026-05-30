"use strict";

const slack = require("./slack-notify.cjs");

const EVENT_TYPE = "fix_ready_for_ai_review";

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

function buildClientPayload({ prNumber, fixOutcome, fixBody }) {
  const normalized = slack.normalizeKnownFixOutcome(fixOutcome);
  if (!normalized) {
    throw new Error(
      `Invalid fix_outcome: ${fixOutcome}. Use ready_for_ai_review, needs_human_decision, split_required, partial_fix, or blocked.`,
    );
  }
  const pr = Number(prNumber);
  if (!Number.isInteger(pr) || pr <= 0) {
    throw new Error(`Invalid pr_number: ${prNumber}`);
  }
  const payload = {
    pr_number: String(pr),
    fix_outcome: normalized,
  };
  const body = nonEmpty(fixBody);
  if (body) payload.fix_body = body;
  return payload;
}

function dispatchUrl(owner, repo) {
  return `https://api.github.com/repos/${owner}/${repo}/dispatches`;
}

async function dispatchPrReadyForAiReview({
  owner,
  repo,
  repository,
  prNumber,
  fixOutcome,
  fixBody,
  token,
  dryRun,
  fetchImpl,
}) {
  const resolved = resolveRepository({ owner, repo, repository });
  const authToken = nonEmpty(token) || nonEmpty(process.env.GITHUB_TOKEN) || nonEmpty(process.env.GH_TOKEN);
  if (!authToken) {
    throw new Error("GITHUB_TOKEN or GH_TOKEN is required to dispatch repository_dispatch");
  }
  const clientPayload = buildClientPayload({ prNumber, fixOutcome, fixBody });
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
    prNumber: "",
    fixOutcome: "ready_for_ai_review",
    fixBody: "",
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
    if (arg === "--fix-outcome") {
      options.fixOutcome = args[++i] || "";
      continue;
    }
    if (arg === "--fix-body-file") {
      const fs = require("fs");
      const filePath = args[++i] || "";
      options.fixBody = fs.readFileSync(filePath, "utf8");
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
  node .github/scripts/dispatch-pr-ready-for-ai-review.cjs \\
    --pr <number> [--fix-outcome ready_for_ai_review] \\
    [--repository owner/repo] [--fix-body-file path] [--dry-run]

Dispatches repository event "${EVENT_TYPE}" to run PR ready-for-AI-review status sync once.
`);
}

async function main() {
  const options = parseCliArgs(process.argv);
  if (options.help) {
    printHelp();
    return;
  }
  const result = await dispatchPrReadyForAiReview(options);
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
  dispatchPrReadyForAiReview,
};
