"use strict";

const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

function nonEmpty(value) {
  return String(value || "").trim();
}

function branchToWorktreeDirName(branchName) {
  return String(branchName || "")
    .trim()
    .replace(/\//g, "-");
}

function resolveDefaultWorktreesRoot(repoRoot) {
  const resolvedRepoRoot = path.resolve(repoRoot);
  const repoDirName = path.basename(resolvedRepoRoot);
  return path.join(path.dirname(resolvedRepoRoot), `${repoDirName}_worktrees`);
}

function parseArgs(argv) {
  const args = argv.slice(2);
  const options = {
    branchName: "",
    repoRoot: process.cwd(),
    worktreesRoot: "",
    dryRun: false,
    json: false,
  };

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === "--branch-name") {
      options.branchName = nonEmpty(args[index + 1]);
      index += 1;
      continue;
    }
    if (arg === "--repo-root") {
      options.repoRoot = nonEmpty(args[index + 1]) || options.repoRoot;
      index += 1;
      continue;
    }
    if (arg === "--worktrees-root") {
      options.worktreesRoot = nonEmpty(args[index + 1]);
      index += 1;
      continue;
    }
    if (arg === "--dry-run") {
      options.dryRun = true;
      continue;
    }
    if (arg === "--json") {
      options.json = true;
      continue;
    }
    throw new Error(`Unknown argument: ${arg}`);
  }

  if (!options.branchName) {
    throw new Error("--branch-name is required");
  }

  options.repoRoot = path.resolve(options.repoRoot);
  options.worktreesRoot = path.resolve(
    options.worktreesRoot || resolveDefaultWorktreesRoot(options.repoRoot),
  );
  return options;
}

function runGit(args, repoRoot) {
  return execFileSync("git", args, {
    cwd: repoRoot,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  }).trim();
}

function listWorktreeEntries(repoRoot) {
  const raw = runGit(["worktree", "list", "--porcelain"], repoRoot);
  const entries = [];
  let current = null;
  for (const line of raw.split(/\r?\n/)) {
    if (line.startsWith("worktree ")) {
      if (current) entries.push(current);
      current = { path: line.slice("worktree ".length).trim(), branch: "" };
      continue;
    }
    if (!current) continue;
    if (line.startsWith("branch ")) {
      current.branch = line.slice("branch ".length).trim();
    }
  }
  if (current) entries.push(current);
  return entries;
}

function findWorktreeByBranch(entries, branchName) {
  const ref = `refs/heads/${branchName}`;
  return entries.find((entry) => entry.branch === ref) || null;
}

function findWorktreeByPath(entries, worktreePath) {
  const resolved = path.resolve(worktreePath);
  return entries.find((entry) => path.resolve(entry.path) === resolved) || null;
}

function localBranchExists(repoRoot, branchName) {
  try {
    runGit(["show-ref", "--verify", "--quiet", `refs/heads/${branchName}`], repoRoot);
    return true;
  } catch {
    return false;
  }
}

function remoteBranchExists(repoRoot, branchName) {
  try {
    runGit(["show-ref", "--verify", "--quiet", `refs/remotes/origin/${branchName}`], repoRoot);
    return true;
  } catch {
    return false;
  }
}

function ensureParentDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function createWorktree(options) {
  const branchName = options.branchName;
  const repoRoot = options.repoRoot;
  const worktreePath = path.join(options.worktreesRoot, branchToWorktreeDirName(branchName));
  const entries = listWorktreeEntries(repoRoot);

  const existingByPath = findWorktreeByPath(entries, worktreePath);
  if (existingByPath) {
    return {
      created: false,
      reason: "already-exists",
      branchName,
      worktreePath: existingByPath.path,
      branch: existingByPath.branch,
    };
  }

  const existingByBranch = findWorktreeByBranch(entries, branchName);
  if (existingByBranch) {
    return {
      created: false,
      reason: "branch-already-checked-out",
      branchName,
      worktreePath: existingByBranch.path,
      branch: existingByBranch.branch,
    };
  }

  if (options.dryRun) {
    return {
      created: true,
      dryRun: true,
      branchName,
      worktreePath,
      worktreesRoot: options.worktreesRoot,
    };
  }

  runGit(["fetch", "origin", branchName], repoRoot);
  ensureParentDir(options.worktreesRoot);

  if (localBranchExists(repoRoot, branchName)) {
    runGit(["worktree", "add", worktreePath, branchName], repoRoot);
  } else if (remoteBranchExists(repoRoot, branchName)) {
    runGit(["worktree", "add", "-b", branchName, worktreePath, `origin/${branchName}`], repoRoot);
  } else {
    throw new Error(`Branch not found locally or on origin: ${branchName}`);
  }

  return {
    created: true,
    branchName,
    worktreePath,
    worktreesRoot: options.worktreesRoot,
  };
}

function printResult(result, json) {
  if (json) {
    process.stdout.write(`${JSON.stringify(result)}\n`);
    return;
  }
  if (result.dryRun) {
    console.log(`[dry_run] worktree: ${result.worktreePath}`);
    return;
  }
  if (result.created) {
    console.log(`Worktree created: ${result.worktreePath}`);
    return;
  }
  console.log(`Worktree skipped (${result.reason}): ${result.worktreePath}`);
}

function main(argv = process.argv) {
  const options = parseArgs(argv);
  const result = createWorktree(options);
  printResult(result, options.json);
  return result;
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    console.error(error.message || String(error));
    process.exit(1);
  }
}

module.exports = {
  branchToWorktreeDirName,
  resolveDefaultWorktreesRoot,
  parseArgs,
  createWorktree,
  listWorktreeEntries,
  findWorktreeByBranch,
  findWorktreeByPath,
};
