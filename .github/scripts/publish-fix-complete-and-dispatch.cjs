"use strict";

const fs = require("fs");
const slack = require("./slack-notify.cjs");
const dispatch = require("./dispatch-pr-ready-for-ai-review.cjs");

const READY_FOR_AI_REVIEW_WORKFLOW_FILE = "pr-ready-for-ai-review.yml";
const DISPATCH_RUN_TITLE_RE = /fix-ready · dispatch · PR #(\d+)/;

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

function resolveFixOutcome({ commentBody, fixOutcomeOverride }) {
  const override = nonEmpty(fixOutcomeOverride);
  if (override) {
    const normalized = slack.normalizeKnownFixOutcome(fixOutcomeOverride);
    if (!normalized) {
      throw new Error(`Invalid fix_outcome override: ${fixOutcomeOverride}`);
    }
    return normalized;
  }
  const extracted = slack.extractFixOutcomeFromComment(commentBody);
  if (!extracted.ok) {
    const reason =
      extracted.reason === "not_fix_complete_comment"
        ? "Comment is not fix-complete-comment format (§1 Fix Outcome required)."
        : "Fix Outcome not found in comment.";
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

function extractPrBodyReplacements(text) {
  const normalized = String(text || "");
  if (!/###\s*PR\s*Body\s*置換/i.test(normalized)) return [];

  const replacements = [];
  for (const row of normalized.matchAll(/^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|/gm)) {
    const find = nonEmpty(row[1]);
    const replace = row[2] ?? "";
    if (!find || find === "find" || find.startsWith("---")) continue;
    replacements.push({ find, replace });
  }
  return replacements;
}

function applyPrBodyReplacements(body, replacements) {
  let next = String(body || "");
  for (const { find, replace } of replacements || []) {
    if (!find || !next.includes(find)) continue;
    next = next.split(find).join(replace);
  }
  return next;
}

async function patchPullRequestBodyFromComment({
  owner,
  repo,
  prNumber,
  commentBody,
  token,
  dryRun,
  fetchImpl,
}) {
  const replacements = extractPrBodyReplacements(commentBody);
  if (!replacements.length) {
    return { ok: true, skipped: true, reason: "no_pr_body_replacements" };
  }

  const pr = Number(prNumber);
  if (!Number.isInteger(pr) || pr <= 0) {
    throw new Error(`Invalid pr_number: ${prNumber}`);
  }

  const send = fetchImpl || global.fetch;
  if (typeof send !== "function") {
    throw new Error("fetch is unavailable");
  }

  const pullUrl = `https://api.github.com/repos/${owner}/${repo}/pulls/${pr}`;
  const pullResponse = await send(pullUrl, { headers: authHeaders(token) });
  if (!pullResponse.ok) {
    const text = await pullResponse.text().catch(() => "");
    throw new Error(`Failed to load PR body: HTTP ${pullResponse.status} ${text}`.trim());
  }
  const pull = await pullResponse.json();
  const currentBody = String(pull.body || "");
  const nextBody = applyPrBodyReplacements(currentBody, replacements);
  if (nextBody === currentBody) {
    return {
      ok: true,
      skipped: true,
      reason: "pr_body_unchanged",
      replacements,
    };
  }

  if (dryRun) {
    return {
      ok: true,
      dryRun: true,
      skipped: false,
      reason: "pr_body_patched",
      replacements,
    };
  }

  const patchResponse = await send(pullUrl, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify({ body: nextBody }),
  });
  if (!patchResponse.ok) {
    const text = await patchResponse.text().catch(() => "");
    throw new Error(`Failed to patch PR body: HTTP ${patchResponse.status} ${text}`.trim());
  }

  return {
    ok: true,
    skipped: false,
    reason: "pr_body_patched",
    replacements,
  };
}

function buildRecoveryCommand({ owner, repo, prNumber, fixOutcome, commentFile }) {
  const repoArg = `--repository ${owner}/${repo}`;
  const parts = [
    "node .github/scripts/publish-fix-complete-and-dispatch.cjs",
    repoArg,
    `--pr ${prNumber}`,
    `--fix-outcome ${fixOutcome}`,
    "--dispatch-only",
  ];
  if (commentFile) parts.push(`--comment-file ${commentFile}`);
  return parts.join(" \\\n  ");
}

async function publishFixCompleteAndDispatch({
  owner,
  repo,
  repository,
  prNumber,
  commentBody,
  commentFile,
  fixOutcome,
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
  const normalizedOutcome = resolveFixOutcome({ commentBody: body, fixOutcomeOverride: fixOutcome });

  let prBodyPatchResult = null;
  if (!dispatchOnly) {
    prBodyPatchResult = await patchPullRequestBodyFromComment({
      owner: resolved.owner,
      repo: resolved.repo,
      prNumber,
      commentBody: body,
      token: authToken,
      dryRun,
      fetchImpl,
    });
  }

  let commentResult = null;
  if (!dispatchOnly) {
    if (!slack.isFixCompleteResultComment(body)) {
      throw new Error(
        "Comment is not fix-complete-comment format. Use prompts/templates/review/fix-complete-comment.md.",
      );
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

  if (normalizedOutcome !== "ready_for_ai_review") {
    return {
      ok: true,
      owner: resolved.owner,
      repo: resolved.repo,
      pr_number: String(prNumber),
      fix_outcome: normalizedOutcome,
      comment: commentResult,
      pr_body_patch: prBodyPatchResult,
      dispatch: null,
      dispatch_skipped: true,
      dispatch_skip_reason: "fix_outcome_not_ready_for_ai_review",
      dispatch_only: Boolean(dispatchOnly),
    };
  }

  try {
    const dispatchResult = await dispatch.dispatchPrReadyForAiReview({
      owner: resolved.owner,
      repo: resolved.repo,
      prNumber,
      fixOutcome: normalizedOutcome,
      fixBody: body,
      token: authToken,
      dryRun,
      fetchImpl,
    });
    return {
      ok: true,
      owner: resolved.owner,
      repo: resolved.repo,
      pr_number: String(prNumber),
      fix_outcome: normalizedOutcome,
      comment: commentResult,
      pr_body_patch: prBodyPatchResult,
      dispatch: dispatchResult,
      dispatch_skipped: false,
      dispatch_only: Boolean(dispatchOnly),
    };
  } catch (error) {
    if (commentResult && !dryRun) {
      error.recoveryCommand = buildRecoveryCommand({
        owner: resolved.owner,
        repo: resolved.repo,
        prNumber,
        fixOutcome: normalizedOutcome,
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

async function listFixReadyDispatchRuns({ owner, repo, token, fetchImpl, perPage = 30 }) {
  const send = fetchImpl || global.fetch;
  const response = await send(
    `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${READY_FOR_AI_REVIEW_WORKFLOW_FILE}/runs?event=repository_dispatch&per_page=${perPage}`,
    { headers: authHeaders(token) },
  );
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Failed to list workflow runs: HTTP ${response.status} ${text}`.trim());
  }
  const data = await response.json();
  return data.workflow_runs || [];
}

function findLatestFixCompleteComment(comments) {
  const sorted = [...(comments || [])].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
  return sorted.find((comment) => {
    if (!slack.isFixCompleteResultComment(comment.body || "")) return false;
    const extracted = slack.extractFixOutcomeFromComment(comment.body || "");
    return extracted.ok && extracted.value === "ready_for_ai_review";
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

async function verifyFixCompleteDispatch({
  owner,
  repo,
  repository,
  prNumber,
  token,
  fetchImpl,
  listComments = listIssueComments,
  listRuns = listFixReadyDispatchRuns,
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
  const latestFixComment = findLatestFixCompleteComment(comments);
  if (!latestFixComment) {
    return {
      ok: false,
      reason: "no_fix_complete_comment",
      message: "No fix-complete comment with ready_for_ai_review found on PR.",
    };
  }

  const extracted = slack.extractFixOutcomeFromComment(latestFixComment.body || "");
  const runs = await listRuns({
    owner: resolved.owner,
    repo: resolved.repo,
    token: authToken,
    fetchImpl,
  });
  const matchedRun = findDispatchRunAfterComment({
    runs,
    prNumber,
    sinceIso: latestFixComment.created_at,
  });

  if (!matchedRun) {
    const recovery = buildRecoveryCommand({
      owner: resolved.owner,
      repo: resolved.repo,
      prNumber,
      fixOutcome: extracted.ok ? extracted.value : "ready_for_ai_review",
    });
    return {
      ok: false,
      reason: "dispatch_missing",
      message: "Fix-complete comment exists but no successful fix-ready dispatch run found after it.",
      latest_fix_complete_comment_url: latestFixComment.html_url || "",
      latest_fix_complete_comment_at: latestFixComment.created_at || "",
      recovery_command: recovery,
    };
  }

  return {
    ok: true,
    pr_number: String(prNumber),
    latest_fix_complete_comment_url: latestFixComment.html_url || "",
    latest_fix_complete_comment_at: latestFixComment.created_at || "",
    dispatch_run_id: matchedRun.id,
    dispatch_run_url: matchedRun.html_url || "",
    dispatch_run_title: matchedRun.display_title || matchedRun.name || "",
    fix_outcome: extracted.ok ? extracted.value : "",
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
    fixOutcome: "",
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
    if (arg === "--fix-outcome") {
      options.fixOutcome = args[++i] || "";
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
  # Post fix-complete comment and dispatch status sync (recommended)
  node .github/scripts/publish-fix-complete-and-dispatch.cjs \\
    --repository owner/repo --pr <number> --comment-file path/to/fix-complete-comment.md

  # Recovery: dispatch only (comment already posted)
  node .github/scripts/publish-fix-complete-and-dispatch.cjs \\
    --repository owner/repo --pr <number> --fix-outcome ready_for_ai_review \\
    --comment-file path/to/fix-complete-comment.md --dispatch-only

  # Verify dispatch was not forgotten
  node .github/scripts/publish-fix-complete-and-dispatch.cjs \\
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
    const result = await verifyFixCompleteDispatch(options);
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
    if (!result.ok) process.exitCode = 1;
    return;
  }

  if (options.dispatchOnly) {
    if (!options.fixOutcome && !options.commentFile && !options.commentBody) {
      throw new Error("--dispatch-only requires --fix-outcome or --comment-file");
    }
  } else if (!options.commentFile && !options.commentBody) {
    throw new Error("--comment-file or --comment-body is required (unless --dispatch-only or --verify)");
  }

  const result = await publishFixCompleteAndDispatch(options);
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = {
  READY_FOR_AI_REVIEW_WORKFLOW_FILE,
  DISPATCH_RUN_TITLE_RE,
  resolveFixOutcome,
  extractPrBodyReplacements,
  applyPrBodyReplacements,
  patchPullRequestBodyFromComment,
  postPullRequestComment,
  publishFixCompleteAndDispatch,
  verifyFixCompleteDispatch,
  findLatestFixCompleteComment,
  findDispatchRunAfterComment,
  buildRecoveryCommand,
};
