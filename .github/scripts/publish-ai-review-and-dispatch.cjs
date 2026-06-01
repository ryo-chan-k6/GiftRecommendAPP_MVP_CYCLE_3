"use strict";

const fs = require("fs");
const slack = require("./slack-notify.cjs");
const dispatch = require("./dispatch-pr-review-status-sync.cjs");

const STATUS_SYNC_WORKFLOW_FILE = "pr-review-status-sync.yml";
const DISPATCH_RUN_TITLE_RE = /status-sync · dispatch · PR #(\d+)/;

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

function readCommentBody({ commentBody, commentFile }) {
  if (nonEmpty(commentBody)) return commentBody;
  if (nonEmpty(commentFile)) return fs.readFileSync(commentFile, "utf8");
  throw new Error("comment body is required (--comment-body or --comment-file)");
}

function resolveReviewResult({ commentBody, reviewResultOverride }) {
  const override = nonEmpty(reviewResultOverride);
  if (override) {
    const normalized = slack.normalizeKnownReviewToken(reviewResultOverride);
    if (!normalized) {
      throw new Error(`Invalid review_result override: ${reviewResultOverride}`);
    }
    return normalized;
  }
  const extracted = slack.extractReviewResultFromAiComment(commentBody);
  if (!extracted.ok) {
    const reason =
      extracted.reason === "not_ai_review_comment"
        ? "Comment is not ai-review-comment format (§1 Review Result required)."
        : extracted.reason === "ambiguous_review_result"
          ? "Review Result is ambiguous in comment."
          : "Review Result not found in comment.";
    throw new Error(reason);
  }
  return extracted.value;
}

function authHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "Content-Type": "application/json",
    "X-GitHub-Api-Version": "2022-11-28",
  };
}

async function postPullRequestComment({
  owner,
  repo,
  prNumber,
  body,
  token,
  dryRun,
  fetchImpl,
}) {
  const pr = Number(prNumber);
  if (!Number.isInteger(pr) || pr <= 0) {
    throw new Error(`Invalid pr_number: ${prNumber}`);
  }
  if (dryRun) {
    return {
      ok: true,
      dryRun: true,
      html_url: `https://github.com/${owner}/${repo}/pull/${pr}#dry-run-comment`,
    };
  }
  const send = fetchImpl || global.fetch;
  if (typeof send !== "function") {
    throw new Error("fetch is unavailable");
  }
  const response = await send(
    `https://api.github.com/repos/${owner}/${repo}/issues/${pr}/comments`,
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ body }),
    },
  );
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Failed to post PR comment: HTTP ${response.status} ${text}`.trim());
  }
  const data = await response.json();
  return { ok: true, html_url: data.html_url || "", id: data.id };
}

function buildRecoveryCommand({ owner, repo, prNumber, reviewResult, commentFile }) {
  const repoArg = `--repository ${owner}/${repo}`;
  const parts = [
    "node .github/scripts/publish-ai-review-and-dispatch.cjs",
    repoArg,
    `--pr ${prNumber}`,
    `--review-result ${reviewResult}`,
    "--dispatch-only",
  ];
  if (commentFile) parts.push(`--comment-file ${commentFile}`);
  return parts.join(" \\\n  ");
}

async function publishAiReviewAndDispatch({
  owner,
  repo,
  repository,
  prNumber,
  commentBody,
  commentFile,
  reviewResult,
  token,
  dryRun,
  dispatchOnly,
  fetchImpl,
}) {
  const resolved = resolveRepository({ owner, repo, repository });
  const authToken = nonEmpty(token) || nonEmpty(process.env.GITHUB_TOKEN) || nonEmpty(process.env.GH_TOKEN);
  if (!authToken) {
    throw new Error("GITHUB_TOKEN or GH_TOKEN is required");
  }

  const body = readCommentBody({ commentBody, commentFile });
  const normalizedResult = resolveReviewResult({ commentBody: body, reviewResultOverride: reviewResult });

  let commentResult = null;
  if (!dispatchOnly) {
    if (!slack.isAiReviewResultComment(body)) {
      throw new Error("Comment is not ai-review-comment format. Use prompts/templates/review/ai-review-comment.md.");
    }
    commentResult = await postPullRequestComment({
      owner: resolved.owner,
      repo: resolved.repo,
      prNumber,
      body,
      token: authToken,
      dryRun,
      fetchImpl,
    });
  }

  try {
    const dispatchResult = await dispatch.dispatchPrReviewStatusSync({
      owner: resolved.owner,
      repo: resolved.repo,
      prNumber,
      reviewResult: normalizedResult,
      reviewBody: body,
      token: authToken,
      dryRun,
      fetchImpl,
    });
    return {
      ok: true,
      owner: resolved.owner,
      repo: resolved.repo,
      pr_number: String(prNumber),
      review_result: normalizedResult,
      comment: commentResult,
      dispatch: dispatchResult,
      dispatch_only: Boolean(dispatchOnly),
    };
  } catch (error) {
    if (commentResult && !dryRun) {
      error.recoveryCommand = buildRecoveryCommand({
        owner: resolved.owner,
        repo: resolved.repo,
        prNumber,
        reviewResult: normalizedResult,
        commentFile,
      });
      error.message = `${error.message}\n\nPR comment was posted but dispatch failed. Re-run dispatch only:\n${error.recoveryCommand}`;
    }
    throw error;
  }
}

async function listIssueComments({ owner, repo, prNumber, token, fetchImpl }) {
  const send = fetchImpl || global.fetch;
  const response = await send(
    `https://api.github.com/repos/${owner}/${repo}/issues/${prNumber}/comments?per_page=100`,
    { headers: authHeaders(token) },
  );
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Failed to list PR comments: HTTP ${response.status} ${text}`.trim());
  }
  return response.json();
}

async function listStatusSyncDispatchRuns({ owner, repo, token, fetchImpl, perPage = 30 }) {
  const send = fetchImpl || global.fetch;
  const response = await send(
    `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${STATUS_SYNC_WORKFLOW_FILE}/runs?event=repository_dispatch&per_page=${perPage}`,
    { headers: authHeaders(token) },
  );
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Failed to list workflow runs: HTTP ${response.status} ${text}`.trim());
  }
  const data = await response.json();
  return data.workflow_runs || [];
}

function findLatestAiReviewComment(comments, { sinceIso } = {}) {
  const since = sinceIso ? new Date(sinceIso).getTime() : NaN;
  const sorted = [...(comments || [])].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
  return sorted.find((comment) => {
    if (!slack.isAiReviewResultComment(comment.body || "")) return false;
    if (!Number.isNaN(since)) {
      const created = new Date(comment.created_at).getTime();
      if (Number.isNaN(created) || created < since) return false;
    }
    return true;
  });
}

function findDispatchRunAfterComment({ runs, prNumber, sinceIso }) {
  const since = new Date(sinceIso).getTime();
  const pr = String(prNumber);
  return (runs || []).find((run) => {
    const title = String(run.display_title || run.name || "");
    const match = DISPATCH_RUN_TITLE_RE.exec(title);
    if (!match || match[1] !== pr) return false;
    const created = new Date(run.created_at).getTime();
    if (Number.isNaN(created) || created < since) return false;
    return run.status === "completed" && run.conclusion === "success";
  });
}

async function verifyAiReviewDispatch({
  owner,
  repo,
  repository,
  prNumber,
  token,
  sinceIso,
  fetchImpl,
  listComments = listIssueComments,
  listRuns = listStatusSyncDispatchRuns,
}) {
  const resolved = resolveRepository({ owner, repo, repository });
  const authToken = nonEmpty(token) || nonEmpty(process.env.GITHUB_TOKEN) || nonEmpty(process.env.GH_TOKEN);
  if (!authToken) {
    throw new Error("GITHUB_TOKEN or GH_TOKEN is required");
  }

  const comments = await listComments({
    owner: resolved.owner,
    repo: resolved.repo,
    prNumber,
    token: authToken,
    fetchImpl,
  });
  const latestAiComment = findLatestAiReviewComment(comments, { sinceIso });
  if (!latestAiComment) {
    return {
      ok: false,
      reason: sinceIso ? "no_ai_review_comment_since_run" : "no_ai_review_comment",
      message: sinceIso
        ? "No AI Review comment found on PR since harness started."
        : "No AI Review comment found on PR.",
    };
  }

  const extracted = slack.extractReviewResultFromAiComment(latestAiComment.body || "");
  const runs = await listRuns({
    owner: resolved.owner,
    repo: resolved.repo,
    token: authToken,
    fetchImpl,
  });
  const matchedRun = findDispatchRunAfterComment({
    runs,
    prNumber,
    sinceIso: latestAiComment.created_at,
  });

  if (!matchedRun) {
    const recovery = buildRecoveryCommand({
      owner: resolved.owner,
      repo: resolved.repo,
      prNumber,
      reviewResult: extracted.ok ? extracted.value : "<review_result>",
    });
    return {
      ok: false,
      reason: "dispatch_missing",
      message: "AI Review comment exists but no successful status-sync dispatch run found after it.",
      latest_ai_review_comment_url: latestAiComment.html_url || "",
      latest_ai_review_comment_at: latestAiComment.created_at || "",
      recovery_command: recovery,
    };
  }

  return {
    ok: true,
    pr_number: String(prNumber),
    latest_ai_review_comment_url: latestAiComment.html_url || "",
    latest_ai_review_comment_at: latestAiComment.created_at || "",
    dispatch_run_id: matchedRun.id,
    dispatch_run_url: matchedRun.html_url || "",
    dispatch_run_title: matchedRun.display_title || matchedRun.name || "",
    review_result: extracted.ok ? extracted.value : "",
  };
}

function parseCliArgs(argv) {
  const args = argv.slice(2);
  const options = {
    owner: "",
    repo: "",
    repository: "",
    prNumber: "",
    commentBody: "",
    commentFile: "",
    reviewResult: "",
    dryRun: false,
    dispatchOnly: false,
    verifyOnly: false,
  };
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--dry-run") {
      options.dryRun = true;
      continue;
    }
    if (arg === "--dispatch-only") {
      options.dispatchOnly = true;
      continue;
    }
    if (arg === "--verify") {
      options.verifyOnly = true;
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
    if (arg === "--comment-body") {
      options.commentBody = args[++i] || "";
      continue;
    }
    if (arg === "--comment-file") {
      options.commentFile = args[++i] || "";
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
  # Post AI Review comment and dispatch status-sync (recommended)
  node .github/scripts/publish-ai-review-and-dispatch.cjs \\
    --repository owner/repo --pr <number> --comment-file path/to/ai-review-comment.md

  # Recovery: dispatch only (comment already posted)
  node .github/scripts/publish-ai-review-and-dispatch.cjs \\
    --repository owner/repo --pr <number> --review-result approve_for_human_review \\
    --comment-file path/to/ai-review-comment.md --dispatch-only

  # Verify dispatch was not forgotten
  node .github/scripts/publish-ai-review-and-dispatch.cjs \\
    --repository owner/repo --pr <number> --verify
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

  if (options.verifyOnly) {
    const result = await verifyAiReviewDispatch(options);
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
    if (!result.ok) process.exitCode = 1;
    return;
  }

  if (options.dispatchOnly) {
    if (!options.reviewResult && !options.commentFile && !options.commentBody) {
      throw new Error("--dispatch-only requires --review-result or --comment-file");
    }
  } else if (!options.commentFile && !options.commentBody) {
    throw new Error("--comment-file or --comment-body is required (unless --dispatch-only or --verify)");
  }

  const result = await publishAiReviewAndDispatch(options);
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = {
  STATUS_SYNC_WORKFLOW_FILE,
  DISPATCH_RUN_TITLE_RE,
  resolveReviewResult,
  postPullRequestComment,
  publishAiReviewAndDispatch,
  verifyAiReviewDispatch,
  findLatestAiReviewComment,
  findDispatchRunAfterComment,
  buildRecoveryCommand,
};
