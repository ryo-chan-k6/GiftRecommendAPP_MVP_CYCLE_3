"use strict";

const slack = require("./slack-notify.cjs");

const EVENT_TYPE = "ai_review_status_sync";

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

function buildClientPayload({ prNumber, reviewResult, reviewBody }) {
  const normalized = slack.normalizeKnownReviewToken(reviewResult);
  if (!normalized) {
    throw new Error(
      `Invalid review_result: ${reviewResult}. Use approve_for_human_review, request_changes, needs_human_decision, split_required, or blocked.`,
    );
  }
  const pr = Number(prNumber);
  if (!Number.isInteger(pr) || pr <= 0) {
    throw new Error(`Invalid pr_number: ${prNumber}`);
  }
  const payload = {
    pr_number: String(pr),
    review_result: normalized,
  };
  const body = nonEmpty(reviewBody);
  if (body) payload.review_body = body;
  return payload;
}

function dispatchUrl(owner, repo) {
  return `https://api.github.com/repos/${owner}/${repo}/dispatches`;
}

async function dispatchPrReviewStatusSync({
  owner,
  repo,
  repository,
  prNumber,
  reviewResult,
  reviewBody,
  token,
  dryRun,
  fetchImpl,
}) {
  const resolved = resolveRepository({ owner, repo, repository });
  const authToken = nonEmpty(token) || nonEmpty(process.env.GITHUB_TOKEN) || nonEmpty(process.env.GH_TOKEN);
  if (!authToken) {
    throw new Error("GITHUB_TOKEN or GH_TOKEN is required to dispatch repository_dispatch");
  }
  const clientPayload = buildClientPayload({ prNumber, reviewResult, reviewBody });
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
    reviewResult: "",
    reviewBody: "",
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
    if (arg === "--review-result") {
      options.reviewResult = args[++i] || "";
      continue;
    }
    if (arg === "--review-body-file") {
      const fs = require("fs");
      const filePath = args[++i] || "";
      options.reviewBody = fs.readFileSync(filePath, "utf8");
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
  node .github/scripts/dispatch-pr-review-status-sync.cjs \\
    --pr <number> --review-result <approve_for_human_review|request_changes|...> \\
    [--repository owner/repo] [--review-body-file path] [--dry-run]

Dispatches repository event "${EVENT_TYPE}" to run PR review status sync once.
`);
}

async function main() {
  const options = parseCliArgs(process.argv);
  if (options.help) {
    printHelp();
    return;
  }
  const result = await dispatchPrReviewStatusSync(options);
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
  dispatchPrReviewStatusSync,
};
