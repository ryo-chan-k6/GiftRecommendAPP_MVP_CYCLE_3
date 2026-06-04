"use strict";

const ALLOWED_AUTOMATION_ACTORS = Object.freeze([
  "github-actions[bot]",
  "github-actions",
]);

/** live-run で target PR head への push を誤検知しない command */
const COMMANDS_EXCLUDING_TARGET_PR_HEAD_REF = Object.freeze([
  "review-pr",
  "fix-review-comments",
]);

const DEFAULT_BRANCH_PROTECTED_PATTERNS = Object.freeze([
  /^refs\/heads\/main$/,
  /^refs\/heads\/develop$/,
]);

function toIsoZulu(value) {
  if (!value) return "";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toISOString();
}

function parseDate(value) {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date;
}

function actorIsAutomation(login) {
  if (!login) return false;
  return ALLOWED_AUTOMATION_ACTORS.includes(String(login));
}

function classifyActor({ login, runActor }) {
  if (actorIsAutomation(login)) return "automation";
  if (runActor && login === runActor) return "definition-run";
  if (!login) return "unknown";
  return "definition-run";
}

function shouldFlagInDryRun({ actorType }) {
  // dry-run では Cloud Agent も既存 workflow も書き込みを行ってはならない。
  // Phase D (live-run 解禁) 時に actorType === "automation" を許容するようロジックを切り替える。
  return ["definition-run", "automation", "unknown"].includes(actorType);
}

async function listIssuesCreatedSince({ octokit, owner, repo, since }) {
  if (!octokit) return [];
  const sinceIso = toIsoZulu(since);
  const params = {
    owner,
    repo,
    state: "all",
    sort: "created",
    direction: "desc",
    per_page: 100,
  };
  if (sinceIso) params.since = sinceIso;
  const issues = octokit.paginate
    ? await octokit.paginate(octokit.rest.issues.listForRepo, params)
    : (await octokit.rest.issues.listForRepo(params)).data;
  const cutoff = parseDate(since);
  return (issues || [])
    .filter((item) => !item.pull_request)
    .filter((item) => !cutoff || (parseDate(item.created_at) && parseDate(item.created_at) >= cutoff));
}

async function listPullsCreatedSince({ octokit, owner, repo, since }) {
  if (!octokit) return [];
  const cutoff = parseDate(since);
  const params = {
    owner,
    repo,
    state: "all",
    sort: "created",
    direction: "desc",
    per_page: 100,
  };
  const pulls = octokit.paginate
    ? await octokit.paginate(octokit.rest.pulls.list, params)
    : (await octokit.rest.pulls.list(params)).data;
  return (pulls || []).filter(
    (item) => !cutoff || (parseDate(item.created_at) && parseDate(item.created_at) >= cutoff),
  );
}

async function resolveTargetPrHeadRef({
  octokit,
  owner,
  repo,
  targetPr,
  getPullImpl,
} = {}) {
  const prNumber = Number(targetPr);
  if (!owner || !repo || !prNumber) return "";
  const getPull =
    getPullImpl ||
    (async () => {
      if (!octokit?.rest?.pulls?.get) return null;
      const res = await octokit.rest.pulls.get({
        owner,
        repo,
        pull_number: prNumber,
      });
      return res.data;
    });
  try {
    const pull = await getPull({ owner, repo, pull_number: prNumber });
    return (pull && pull.head && pull.head.ref) || "";
  } catch {
    return "";
  }
}

async function listBranchesCreatedSince({ octokit, owner, repo, since }) {
  if (!octokit) return [];
  const cutoff = parseDate(since);
  const branches = octokit.paginate
    ? await octokit.paginate(octokit.rest.repos.listBranches, {
        owner,
        repo,
        per_page: 100,
      })
    : (
        await octokit.rest.repos.listBranches({
          owner,
          repo,
          per_page: 100,
        })
      ).data;
  const candidates = [];
  for (const branch of branches || []) {
    const sha = branch.commit && branch.commit.sha;
    if (!sha) continue;
    let commit;
    try {
      const res = await octokit.rest.repos.getCommit({ owner, repo, ref: sha });
      commit = res.data;
    } catch {
      continue;
    }
    const committed = parseDate(
      commit.commit && (commit.commit.committer || commit.commit.author) &&
        (commit.commit.committer?.date || commit.commit.author?.date),
    );
    if (!cutoff || (committed && committed >= cutoff)) {
      candidates.push({
        name: branch.name,
        sha,
        committed_at: committed ? committed.toISOString() : "",
        author_login: (commit.author && commit.author.login) || "",
        committer_login: (commit.committer && commit.committer.login) || "",
      });
    }
  }
  return candidates;
}

function describeIssueViolation(issue, runActor) {
  const login = (issue.user && issue.user.login) || "";
  const actorType = classifyActor({ login, runActor });
  return {
    type: "issue",
    number: issue.number,
    title: issue.title || "",
    url: issue.html_url || "",
    created_at: issue.created_at || "",
    actor_login: login,
    actor_type: actorType,
  };
}

function describePullViolation(pull, runActor) {
  const login = (pull.user && pull.user.login) || "";
  const actorType = classifyActor({ login, runActor });
  return {
    type: "pull_request",
    number: pull.number,
    title: pull.title || "",
    url: pull.html_url || "",
    created_at: pull.created_at || "",
    actor_login: login,
    actor_type: actorType,
  };
}

function describeReviewDispatchViolation({ prNumber, verifyResult }) {
  return {
    type: "review_dispatch",
    number: Number(prNumber),
    title: verifyResult.reason || verifyResult.message || "dispatch_missing",
    url: verifyResult.latest_ai_review_comment_url || verifyResult.recovery_command || "",
    created_at: verifyResult.latest_ai_review_comment_at || "",
    actor_login: "-",
    actor_type: "review_dispatch",
    recovery_command: verifyResult.recovery_command || "",
  };
}

function describeReviewCommentTruncatedViolation({ prNumber, verifyResult }) {
  return {
    type: "review_comment_truncated",
    number: Number(prNumber),
    title: "ai_review_comment_truncated",
    url: verifyResult.latest_ai_review_comment_url || "",
    created_at: verifyResult.latest_ai_review_comment_at || "",
    actor_login: "-",
    actor_type: "review_comment_truncated",
  };
}

async function runReviewPrDispatchVerify({
  owner,
  repo,
  targetPr,
  token,
  startedAt,
  fetchImpl,
  verifyImpl,
}) {
  if (!targetPr) {
    return { ok: true, skipped: true, reason: "no_target_pr" };
  }
  const publish = require("./publish-ai-review-and-dispatch.cjs");
  const verify =
    verifyImpl ||
    ((options) =>
      publish.verifyAiReviewDispatch({
        owner,
        repo,
        prNumber: targetPr,
        token,
        sinceIso: startedAt,
        fetchImpl,
      }));
  return verify({ owner, repo, prNumber: targetPr, token, sinceIso: startedAt, fetchImpl });
}

function describeBranchViolation(branch, runActor) {
  const login = branch.author_login || branch.committer_login || "";
  const actorType = classifyActor({ login, runActor });
  return {
    type: "branch",
    name: branch.name,
    sha: branch.sha,
    url: "",
    created_at: branch.committed_at || "",
    actor_login: login,
    actor_type: actorType,
  };
}

async function runPostVerify({
  octokit,
  owner,
  repo,
  startedAt,
  runMode,
  runActor,
  command,
  targetPr,
  token,
  fetchImpl,
  verifyImpl,
  listIssues = listIssuesCreatedSince,
  listPulls = listPullsCreatedSince,
  listBranches = listBranchesCreatedSince,
  getPullImpl,
} = {}) {
  if (!owner || !repo) {
    throw new Error("owner / repo are required");
  }
  if (!startedAt) {
    throw new Error("startedAt is required");
  }
  const mode = String(runMode || "").trim();
  const issues = await listIssues({ octokit, owner, repo, since: startedAt });
  const pulls = await listPulls({ octokit, owner, repo, since: startedAt });
  const branches = await listBranches({ octokit, owner, repo, since: startedAt });

  let excludedPrHeadRef = "";
  const cmd = String(command || "").trim();
  if (COMMANDS_EXCLUDING_TARGET_PR_HEAD_REF.includes(cmd) && targetPr) {
    excludedPrHeadRef = await resolveTargetPrHeadRef({
      octokit,
      owner,
      repo,
      targetPr,
      getPullImpl,
    });
  }
  const branchCandidates =
    excludedPrHeadRef && branches.length
      ? branches.filter((branch) => branch.name !== excludedPrHeadRef)
      : branches;

  const candidates = [
    ...issues.map((item) => describeIssueViolation(item, runActor)),
    ...pulls.map((item) => describePullViolation(item, runActor)),
    ...branches.map((item) => describeBranchViolation(item, runActor)),
  ];

  let violations = [];
  if (mode === "dry-run") {
    violations = candidates.filter((candidate) => {
      if (
        candidate.type === "branch" &&
        excludedPrHeadRef &&
        candidate.name === excludedPrHeadRef
      ) {
        return false;
      }
      return shouldFlagInDryRun({ actorType: candidate.actor_type });
    });
  } else {
    // live-run の actor 区別ロジックは Phase D で有効化する。
    // 想定: automation 由来は許容、definition-run 由来のうち Branch / PR 作成は違反。
    // ここでは MVP の安全側として、未知の actor / definition-run actor の Branch / PR を flag する。
    violations = candidates.filter((candidate) => {
      if (candidate.type === "issue") return false; // Issue 起票は許容
      if (candidate.actor_type === "automation") return false;
      if (
        candidate.type === "branch" &&
        excludedPrHeadRef &&
        candidate.name === excludedPrHeadRef
      ) {
        return false;
      }
      return true;
    });
  }

  let dispatchVerify = null;
  if (String(command || "").trim() === "review-pr" && mode === "live-run" && targetPr) {
    dispatchVerify = await runReviewPrDispatchVerify({
      owner,
      repo,
      targetPr,
      token,
      startedAt,
      fetchImpl,
      verifyImpl,
    });
    if (!dispatchVerify.ok && !dispatchVerify.skipped) {
      violations.push(
        describeReviewDispatchViolation({ prNumber: targetPr, verifyResult: dispatchVerify }),
      );
    } else if (dispatchVerify.ok && dispatchVerify.latest_ai_review_comment_truncated) {
      // dispatch は成立しているが、投稿済みコメント本文が切り詰められている。
      violations.push(
        describeReviewCommentTruncatedViolation({ prNumber: targetPr, verifyResult: dispatchVerify }),
      );
    }
  }

  return {
    started_at: toIsoZulu(startedAt),
    run_mode: mode,
    command: String(command || "").trim() || undefined,
    target_pr: targetPr || undefined,
    dispatch_verify: dispatchVerify || undefined,
    excluded_pr_head_ref: excludedPrHeadRef || undefined,
    counts: {
      issues: issues.length,
      pull_requests: pulls.length,
      branches: branchCandidates.length,
      violations: violations.length,
    },
    candidates,
    violations,
  };
}

function formatViolationsMarkdown(result) {
  if (!result) return "### Guard Violations (post-run)\n- None\n";
  const lines = ["### Guard Violations (post-run)"];
  lines.push("");
  lines.push(
    `- run_mode: \`${result.run_mode || "-"}\` / scanned since \`${result.started_at || "-"}\``,
  );
  lines.push(
    `- counts: issues=${result.counts.issues}, prs=${result.counts.pull_requests}, branches=${result.counts.branches}, violations=${result.counts.violations}`,
  );
  if (!result.violations.length) {
    lines.push("- result: None");
    if (result.dispatch_verify && result.dispatch_verify.ok) {
      lines.push(
        `- review_dispatch: ok (PR #${result.target_pr || "-"}, run ${result.dispatch_verify.dispatch_run_id || "-"})`,
      );
    }
    return `${lines.join("\n")}\n`;
  }
  lines.push("");
  lines.push("| type | identifier | actor | created_at | url |");
  lines.push("| ---- | ---------- | ----- | ---------- | --- |");
  for (const violation of result.violations) {
    const identifier =
      violation.type === "branch"
        ? `\`${violation.name}\` (${(violation.sha || "").slice(0, 7)})`
        : violation.type === "review_dispatch" || violation.type === "review_comment_truncated"
          ? `PR #${violation.number} ${violation.title || ""}`.trim()
          : `#${violation.number} ${violation.title || ""}`.trim();
    const actor = `${violation.actor_login || "-"} (${violation.actor_type})`;
    const url = violation.url || "-";
    lines.push(
      `| ${violation.type} | ${identifier} | ${actor} | ${violation.created_at || "-"} | ${url} |`,
    );
  }
  return `${lines.join("\n")}\n`;
}

module.exports = {
  ALLOWED_AUTOMATION_ACTORS,
  DEFAULT_BRANCH_PROTECTED_PATTERNS,
  actorIsAutomation,
  classifyActor,
  describeBranchViolation,
  describeIssueViolation,
  describePullViolation,
  describeReviewDispatchViolation,
  describeReviewCommentTruncatedViolation,
  formatViolationsMarkdown,
  listBranchesCreatedSince,
  listIssuesCreatedSince,
  listPullsCreatedSince,
  parseDate,
  resolveTargetPrHeadRef,
  runPostVerify,
  runReviewPrDispatchVerify,
  shouldFlagInDryRun,
  toIsoZulu,
};
