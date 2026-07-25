"use strict";

const fs = require("fs");
const slack = require("./slack-notify.cjs");
const dispatch = require("./dispatch-pr-review-status-sync.cjs");

const STATUS_SYNC_WORKFLOW_FILE = "pr-review-status-sync.yml";
const STATUS_SYNC_PROJECT_JOB_NAME = "sync-project-status";
const DISPATCH_RUN_TITLE_RE = /status-sync · dispatch · PR #(\d+)/;
const STATUS_SYNC_VERIFY_POLL_MS = 5000;
const STATUS_SYNC_VERIFY_MAX_WAIT_MS = 120000;

// Cloud Agent が本文を自身のサンドボックスへ退避し、コメント本文を省略・参照で
// 代替してしまう切り詰めパターン。これらを含む本文は不完全とみなし投稿を拒否する。
const TRUNCATION_PATTERNS = Object.freeze([
  // ローカル一時ファイル参照（例: /tmp/ai-review-comment-302.md）
  /(?:^|[\s`(（])\/(?:tmp|var\/folders|private\/tmp)\/[^\s`)）]+\.(?:md|markdown|txt)/i,
  // 「全文は … を参照」のような本文退避表現
  /全文[はを][\s\S]{0,40}参照/,
  /(?:full\s+(?:text|body|version)|complete\s+(?:text|body))[\s\S]{0,40}(?:see|refer)/i,
  // 省略を示す単独の三点リーダ行
  /^\s*(?:\.{3}|…|\.{3}\s*\(.*\)|…\s*\(.*\))\s*$/m,
]);

// NG理由サマリが必須となる Review Result（Human 判断 / Issue #466）
const RESULTS_REQUIRING_NG_REASON_SUMMARY = Object.freeze([
  "request_changes",
  "blocked",
  "split_required",
  "needs_human_decision",
]);

const NG_REASON_SUMMARY_HEADING_RE = /^##\s*NG理由サマリ\s*$/m;
const MAX_NG_REASON_SUMMARY_ITEMS = 10;

function nonEmpty(value) {
  return String(value || "").trim();
}

// AI Review コメント本文が切り詰め（本文退避・省略）されているかを判定する。
function isTruncatedAiReviewComment(body) {
  const text = String(body || "");
  if (!text) return false;
  return TRUNCATION_PATTERNS.some((pattern) => pattern.test(text));
}

function requiresNgReasonSummary(reviewResult) {
  const token = slack.normalizeReviewResult(reviewResult);
  return Boolean(token && RESULTS_REQUIRING_NG_REASON_SUMMARY.includes(token));
}

function extractNgReasonSummarySection(body) {
  const text = String(body || "");
  const match = NG_REASON_SUMMARY_HEADING_RE.exec(text);
  if (!match) return "";
  const start = match.index + match[0].length;
  const rest = text.slice(start);
  const nextHeading = /^##\s+/m.exec(rest);
  const section = nextHeading ? rest.slice(0, nextHeading.index) : rest;
  return section.trim();
}

function hasUsableNgReasonSummary(body) {
  const section = extractNgReasonSummarySection(body);
  if (!section) return false;
  const lines = section
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  // 説明文のみ・「なし」のみは未記載扱い
  const bullets = lines.filter((line) => /^[-*]\s+/.test(line));
  const usableBullets = bullets.filter((line) => !/^[-*]\s*なし\s*$/.test(line));
  if (usableBullets.length > 0) return true;
  if (/他\d+件は/.test(section)) return true;
  // 箇条書き以外の実質テキスト（「なし」やテンプレ説明を除く）
  const prose = lines.filter(
    (line) =>
      !/^[-*]\s+/.test(line) &&
      line !== "なし" &&
      !line.includes("のとき **必須**") &&
      !line.includes("のとき必須") &&
      !line.includes("指摘レベル") &&
      !line.includes("最大") &&
      !line.includes("approve_for_human_review") &&
      !line.includes("該当がない場合"),
  );
  return prose.some((line) => line.length > 0 && line !== "なし");
}

function isMissingNgReasonSummary(body, reviewResult) {
  let token = slack.normalizeReviewResult(reviewResult);
  if (!token) {
    const extracted = slack.extractReviewResultFromAiComment(body);
    token = extracted.ok ? extracted.value : "";
  }
  if (!requiresNgReasonSummary(token)) return false;
  return !hasUsableNgReasonSummary(body);
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
    if (isTruncatedAiReviewComment(body)) {
      throw new Error(
        "Comment appears truncated (local file reference / omission marker). " +
          "Post the full AI Review comment body verbatim, not a /tmp reference or summary.",
      );
    }
    if (isMissingNgReasonSummary(body, normalizedResult)) {
      throw new Error(
        "Comment is missing required ## NG理由サマリ for " +
          `${normalizedResult}. Include must-level fix summaries (max ${MAX_NG_REASON_SUMMARY_ITEMS}).`,
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

function filterDispatchRunsAfterComment({ runs, prNumber, sinceIso }) {
  const since = new Date(sinceIso).getTime();
  const pr = String(prNumber);
  return (runs || []).filter((run) => {
    const title = String(run.display_title || run.name || "");
    const match = DISPATCH_RUN_TITLE_RE.exec(title);
    if (!match || match[1] !== pr) return false;
    const created = new Date(run.created_at).getTime();
    if (Number.isNaN(created) || created < since) return false;
    return true;
  });
}

async function fetchWorkflowRunJobs({ owner, repo, runId, token, fetchImpl }) {
  const send = fetchImpl || global.fetch;
  const response = await send(
    `https://api.github.com/repos/${owner}/${repo}/actions/runs/${runId}/jobs`,
    { headers: authHeaders(token) },
  );
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Failed to list workflow jobs: HTTP ${response.status} ${text}`.trim());
  }
  const data = await response.json();
  return data.jobs || [];
}

async function statusSyncProjectJobSucceeded({ owner, repo, run, token, fetchImpl }) {
  if (!run || run.status !== "completed") return false;
  try {
    const jobs = await fetchWorkflowRunJobs({
      owner,
      repo,
      runId: run.id,
      token,
      fetchImpl,
    });
    const syncJob = jobs.find((job) => job.name === STATUS_SYNC_PROJECT_JOB_NAME);
    if (syncJob) {
      return syncJob.status === "completed" && syncJob.conclusion === "success";
    }
  } catch {
    // workflow jobs API が利用できない場合は workflow 全体の conclusion にフォールバック
  }
  return run.conclusion === "success";
}

async function findDispatchRunAfterComment({
  owner,
  repo,
  runs,
  prNumber,
  sinceIso,
  token,
  fetchImpl,
}) {
  const candidates = filterDispatchRunsAfterComment({ runs, prNumber, sinceIso }).sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
  for (const run of candidates) {
    if (await statusSyncProjectJobSucceeded({ owner, repo, run, token, fetchImpl })) {
      return run;
    }
  }
  return null;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function verifyAiReviewDispatch({
  owner,
  repo,
  repository,
  prNumber,
  token,
  sinceIso,
  fetchImpl,
  pollMaxWaitMs = STATUS_SYNC_VERIFY_MAX_WAIT_MS,
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
  const sinceForRuns = latestAiComment.created_at;
  const waitMs = Number.isFinite(pollMaxWaitMs) ? Math.max(0, pollMaxWaitMs) : STATUS_SYNC_VERIFY_MAX_WAIT_MS;
  const deadline = Date.now() + waitMs;
  let matchedRun = null;
  do {
    const runs = await listRuns({
      owner: resolved.owner,
      repo: resolved.repo,
      token: authToken,
      fetchImpl,
    });
    matchedRun = await findDispatchRunAfterComment({
      owner: resolved.owner,
      repo: resolved.repo,
      runs,
      prNumber,
      sinceIso: sinceForRuns,
      token: authToken,
      fetchImpl,
    });
    if (matchedRun || waitMs === 0 || Date.now() >= deadline) break;
    await sleep(STATUS_SYNC_VERIFY_POLL_MS);
  } while (Date.now() <= deadline);

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

  const commentBody = latestAiComment.body || "";
  const reviewResult = extracted.ok ? extracted.value : "";
  return {
    ok: true,
    pr_number: String(prNumber),
    latest_ai_review_comment_url: latestAiComment.html_url || "",
    latest_ai_review_comment_at: latestAiComment.created_at || "",
    latest_ai_review_comment_truncated: isTruncatedAiReviewComment(commentBody),
    latest_ai_review_comment_missing_ng_summary: isMissingNgReasonSummary(commentBody, reviewResult),
    dispatch_run_id: matchedRun.id,
    dispatch_run_url: matchedRun.html_url || "",
    dispatch_run_title: matchedRun.display_title || matchedRun.name || "",
    review_result: reviewResult,
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
  TRUNCATION_PATTERNS,
  RESULTS_REQUIRING_NG_REASON_SUMMARY,
  MAX_NG_REASON_SUMMARY_ITEMS,
  isTruncatedAiReviewComment,
  requiresNgReasonSummary,
  extractNgReasonSummarySection,
  hasUsableNgReasonSummary,
  isMissingNgReasonSummary,
  resolveReviewResult,
  postPullRequestComment,
  publishAiReviewAndDispatch,
  verifyAiReviewDispatch,
  findLatestAiReviewComment,
  findDispatchRunAfterComment,
  buildRecoveryCommand,
};
