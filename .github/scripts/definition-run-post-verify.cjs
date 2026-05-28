"use strict";

const ALLOWED_AUTOMATION_ACTORS = Object.freeze([
  "github-actions[bot]",
  "github-actions",
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
  listIssues = listIssuesCreatedSince,
  listPulls = listPullsCreatedSince,
  listBranches = listBranchesCreatedSince,
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

  const candidates = [
    ...issues.map((item) => describeIssueViolation(item, runActor)),
    ...pulls.map((item) => describePullViolation(item, runActor)),
    ...branches.map((item) => describeBranchViolation(item, runActor)),
  ];

  let violations = [];
  if (mode === "dry-run") {
    violations = candidates.filter((candidate) => shouldFlagInDryRun({ actorType: candidate.actor_type }));
  } else {
    // live-run の actor 区別ロジックは Phase D で有効化する。
    // 想定: automation 由来は許容、definition-run 由来のうち Branch / PR 作成は違反。
    // ここでは MVP の安全側として、未知の actor / definition-run actor の Branch / PR を flag する。
    violations = candidates.filter((candidate) => {
      if (candidate.type === "issue") return false; // Issue 起票は許容
      if (candidate.actor_type === "automation") return false;
      return true;
    });
  }

  return {
    started_at: toIsoZulu(startedAt),
    run_mode: mode,
    counts: {
      issues: issues.length,
      pull_requests: pulls.length,
      branches: branches.length,
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
    return `${lines.join("\n")}\n`;
  }
  lines.push("");
  lines.push("| type | identifier | actor | created_at | url |");
  lines.push("| ---- | ---------- | ----- | ---------- | --- |");
  for (const violation of result.violations) {
    const identifier =
      violation.type === "branch"
        ? `\`${violation.name}\` (${(violation.sha || "").slice(0, 7)})`
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
  formatViolationsMarkdown,
  listBranchesCreatedSince,
  listIssuesCreatedSince,
  listPullsCreatedSince,
  parseDate,
  runPostVerify,
  shouldFlagInDryRun,
  toIsoZulu,
};
