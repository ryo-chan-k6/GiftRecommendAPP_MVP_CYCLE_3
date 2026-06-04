"use strict";

const fs = require("node:fs");
const path = require("node:path");
const slack = require("./slack-notify.cjs");
const resolver = require("./resolve-review-definition.cjs");

function nonEmpty(value) {
  return String(value || "").trim();
}

function readReviewDefinitionIssue(workspaceRoot, reviewDefinitionPath) {
  const relative = nonEmpty(reviewDefinitionPath);
  if (!relative) return 0;
  const absolute = path.join(workspaceRoot, relative);
  let content = "";
  try {
    content = fs.readFileSync(absolute, "utf8");
  } catch {
    return 0;
  }
  return resolver.extractTargetIssueNumber(content) || 0;
}

function resolveHarnessRequestIssue({
  workspaceRoot,
  pull,
  issueNumberArg = "",
  reviewDefinitionPath = "",
}) {
  const workspace = nonEmpty(workspaceRoot) || process.cwd();
  const fromReview = readReviewDefinitionIssue(workspace, reviewDefinitionPath);
  if (fromReview > 0) return fromReview;

  const fromTarget = slack.resolveStatusSyncTargetIssue({
    prBody: pull?.body || "",
    headRef: pull?.head?.ref || "",
  });
  if (fromTarget > 0) return fromTarget;

  const parsed = Number(issueNumberArg);
  if (Number.isInteger(parsed) && parsed > 0) return parsed;

  return resolver.parseBranchRef(pull?.head?.ref || "")?.issueNumber || null;
}

module.exports = {
  resolveHarnessRequestIssue,
  readReviewDefinitionIssue,
};
