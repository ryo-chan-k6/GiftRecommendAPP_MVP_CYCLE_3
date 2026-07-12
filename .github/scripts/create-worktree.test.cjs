"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");

const {
  branchToWorktreeDirName,
  resolveDefaultWorktreesRoot,
  parseArgs,
} = require("./create-worktree.cjs");

test("branchToWorktreeDirName replaces slash with hyphen", () => {
  assert.equal(
    branchToWorktreeDirName("chore/task-471-worktree-auto-create"),
    "chore-task-471-worktree-auto-create",
  );
});

test("resolveDefaultWorktreesRoot uses sibling _worktrees directory", () => {
  assert.equal(
    resolveDefaultWorktreesRoot("/home/user/GiftRecommendAPP_MVP_CYCLE_3"),
    "/home/user/GiftRecommendAPP_MVP_CYCLE_3_worktrees",
  );
});

test("parseArgs requires branch name and resolves defaults", () => {
  const options = parseArgs([
    "node",
    "create-worktree.cjs",
    "--branch-name",
    "docs/task-111-api-design",
    "--repo-root",
    "/tmp/repo",
    "--json",
  ]);
  assert.equal(options.branchName, "docs/task-111-api-design");
  assert.equal(options.repoRoot, "/tmp/repo");
  assert.equal(options.worktreesRoot, "/tmp/repo_worktrees");
  assert.equal(options.json, true);
  assert.equal(options.dryRun, false);
});

test("parseArgs rejects missing branch name", () => {
  assert.throws(() => parseArgs(["node", "create-worktree.cjs"]), /--branch-name is required/);
});
