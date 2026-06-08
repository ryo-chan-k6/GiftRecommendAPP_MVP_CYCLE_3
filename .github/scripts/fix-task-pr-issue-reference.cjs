"use strict";

const resolver = require("./resolve-review-definition.cjs");

function nonEmpty(value) {
  return String(value || "").trim();
}

function authHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "Content-Type": "application/json",
    "X-GitHub-Api-Version": "2022-11-28",
  };
}

async function fetchJson(url, { token, method = "GET", body, fetchImpl }) {
  const send = fetchImpl || global.fetch;
  if (typeof send !== "function") {
    throw new Error("fetch is unavailable");
  }
  const response = await send(url, {
    method,
    headers: authHeaders(token),
    body: body == null ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`GitHub API failed: HTTP ${response.status} ${text}`.trim());
  }
  if (response.status === 204) return null;
  return response.json();
}

function normalizeTaskPrIssueReference(body, taskIssueNumber) {
  const issueNumber = Number(taskIssueNumber);
  if (!Number.isInteger(issueNumber) || issueNumber <= 0) {
    return { changed: false, body: String(body || ""), reason: "invalid_issue_number" };
  }

  const text = String(body || "");
  const closesPattern = new RegExp(`\\bCloses\\s+#${issueNumber}\\b`, "i");
  if (!closesPattern.test(text)) {
    return { changed: false, body: text, reason: "closes_not_found" };
  }

  const updated = text.replace(closesPattern, `Related to #${issueNumber}`);
  return {
    changed: updated !== text,
    body: updated,
    reason: updated !== text ? "replaced_closes_with_related_to" : "no_change",
  };
}

async function fixTaskPrIssueReference({
  owner,
  repo,
  repository,
  prNumber,
  token,
  dryRun,
  fetchImpl,
}) {
  const resolvedRepo = repository
    ? { owner: repository.split("/")[0], repo: repository.split("/")[1] }
    : { owner, repo };
  const authToken = nonEmpty(token);
  if (!authToken) {
    throw new Error("token is required");
  }
  const pr = Number(prNumber);
  if (!Number.isInteger(pr) || pr <= 0) {
    throw new Error(`Invalid pr_number: ${prNumber}`);
  }

  const pull = await fetchJson(
    `https://api.github.com/repos/${resolvedRepo.owner}/${resolvedRepo.repo}/pulls/${pr}`,
    { token: authToken, fetchImpl },
  );
  const branchInfo = resolver.parseBranchRef(pull?.head?.ref || "");
  if (!branchInfo || branchInfo.unit !== "task") {
    return {
      ok: true,
      skipped: true,
      reason: "not_task_branch",
      head_ref: pull?.head?.ref || "",
    };
  }

  const normalized = normalizeTaskPrIssueReference(pull.body || "", branchInfo.issueNumber);
  if (!normalized.changed) {
    return {
      ok: true,
      skipped: true,
      reason: normalized.reason,
      task_issue_number: branchInfo.issueNumber,
      head_ref: pull?.head?.ref || "",
    };
  }

  if (dryRun) {
    return {
      ok: true,
      skipped: false,
      dryRun: true,
      reason: normalized.reason,
      task_issue_number: branchInfo.issueNumber,
      head_ref: pull?.head?.ref || "",
    };
  }

  await fetchJson(
    `https://api.github.com/repos/${resolvedRepo.owner}/${resolvedRepo.repo}/pulls/${pr}`,
    {
      token: authToken,
      method: "PATCH",
      body: { body: normalized.body },
      fetchImpl,
    },
  );

  return {
    ok: true,
    skipped: false,
    reason: normalized.reason,
    task_issue_number: branchInfo.issueNumber,
    head_ref: pull?.head?.ref || "",
  };
}

function parseCliArgs(argv) {
  const args = argv.slice(2);
  const options = {
    owner: "",
    repo: "",
    repository: "",
    prNumber: "",
    dryRun: false,
  };
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--dry-run") {
      options.dryRun = true;
      continue;
    }
    if (arg === "--repository" || arg === "-R") {
      options.repository = args[++i] || "";
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
    if (arg === "--pr" || arg === "--pr-number") {
      options.prNumber = args[++i] || "";
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
  node .github/scripts/fix-task-pr-issue-reference.cjs \\
    --repository owner/repo \\
    --pr <number> \\
    [--dry-run]

Replaces Task PR body "Closes #<taskIssue>" with "Related to #<taskIssue>" when Branch is task-*.
`);
}

async function main() {
  const options = parseCliArgs(process.argv);
  if (options.help) {
    printHelp();
    return;
  }
  if (!options.prNumber) {
    throw new Error("--pr is required");
  }
  const result = await fixTaskPrIssueReference(options);
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = {
  normalizeTaskPrIssueReference,
  fixTaskPrIssueReference,
};
