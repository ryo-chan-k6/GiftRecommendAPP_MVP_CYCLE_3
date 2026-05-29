"use strict";

const MARKER_PREFIX = "slack-thread:v1";
const SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage";
const AI_REVIEW_HEADING_1 = "## 1. レビュー結果";
const AI_REVIEW_HEADING_22 = "## 22. Status更新意図";
const AUTOMATION_STATUS_COMMENT_PREFIX = "Project Status更新意図:";
const SLACK_THREAD_MARKER_NOTE = "Slack thread marker for GitHub Actions automation.";
const KNOWN_REVIEW_RESULTS = [
  "approve_for_human_review",
  "request_changes",
  "needs_human_decision",
  "split_required",
  "blocked",
];

function nonEmpty(value) {
  return String(value || "").trim();
}

function levelLabel(level) {
  const value = nonEmpty(level).toLowerCase();
  if (["info", "review", "action_required", "warning", "error"].includes(value)) return value;
  return "info";
}

function buildThreadKey({ owner, repo, kind, number }) {
  return `${kind}:${owner}/${repo}#${number}`;
}

function renderPairs(pairs) {
  if (!pairs) return [];
  if (Array.isArray(pairs)) {
    return pairs
      .map((item) => {
        if (Array.isArray(item)) return [item[0], item[1]];
        return [item.label || item.name || item.key, item.value];
      })
      .filter(([key, value]) => nonEmpty(key) && nonEmpty(value));
  }
  return Object.entries(pairs).filter(([, value]) => nonEmpty(value));
}

function buildSlackText(input = {}) {
  const level = levelLabel(input.level);
  const title = nonEmpty(input.title) || "通知";
  const lines = [];
  const mention = nonEmpty(input.mention);
  if (mention) lines.push(mention);
  lines.push(`*[${level}] ${title}*`);

  const summary = nonEmpty(input.summary);
  if (summary) {
    lines.push("");
    lines.push("*概要:*");
    lines.push(summary);
  }

  const fields = renderPairs(input.fields);
  if (fields.length) {
    lines.push("");
    lines.push("*対象:*");
    for (const [key, value] of fields) {
      lines.push(`- ${key}: ${value}`);
    }
  }

  const humanAction = nonEmpty(input.humanAction);
  if (humanAction) {
    lines.push("");
    lines.push("*人間に必要な対応:*");
    lines.push(humanAction);
  }

  const links = renderPairs(input.links);
  if (links.length) {
    lines.push("");
    lines.push("*リンク:*");
    for (const [key, value] of links) {
      lines.push(`- ${key}: ${value}`);
    }
  }

  return lines.join("\n");
}

function markerValue(value) {
  return encodeURIComponent(nonEmpty(value));
}

function unmarkerValue(value) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function buildThreadMarker({ threadKey, channel, ts }) {
  const key = markerValue(threadKey);
  const ch = markerValue(channel);
  const threadTs = markerValue(ts);
  return `<!-- ${MARKER_PREFIX} key=${key} channel=${ch} ts=${threadTs} -->`;
}

function parseMarkerAttrs(raw) {
  const attrs = {};
  for (const match of raw.matchAll(/([a-zA-Z_][a-zA-Z0-9_]*)=([^\s]+)/g)) {
    attrs[match[1]] = unmarkerValue(match[2]);
  }
  return attrs;
}

function extractThreadMarkers(body) {
  const markers = [];
  const text = String(body || "");
  const re = /<!--\s*slack-thread:v1\s+([^>]+?)\s*-->/g;
  for (const match of text.matchAll(re)) {
    const attrs = parseMarkerAttrs(match[1]);
    if (attrs.key && attrs.ts) markers.push(attrs);
  }
  return markers;
}

function findThreadTsFromComments(comments, threadKey, channel) {
  const items = Array.isArray(comments) ? comments : [];
  for (const comment of [...items].reverse()) {
    for (const marker of extractThreadMarkers(comment.body || "")) {
      if (marker.key !== threadKey) continue;
      if (channel && marker.channel && marker.channel !== channel) continue;
      return marker.ts;
    }
  }
  return "";
}

function buildThreadMarkerCommentBody({ threadKey, channel, ts }) {
  return [
    buildThreadMarker({ threadKey, channel, ts }),
    "",
    "Slack thread marker for GitHub Actions automation.",
    "Do not edit this comment manually.",
  ].join("\n");
}

async function listIssueComments({ github, owner, repo, issueNumber }) {
  if (github.paginate) {
    return github.paginate(github.rest.issues.listComments, {
      owner,
      repo,
      issue_number: issueNumber,
      per_page: 100,
    });
  }
  const { data } = await github.rest.issues.listComments({
    owner,
    repo,
    issue_number: issueNumber,
    per_page: 100,
  });
  return data;
}

async function upsertThreadMarkerComment({ github, owner, repo, issueNumber, threadKey, channel, ts, comments, dryRun }) {
  if (!ts) return { ok: false, skipped: true, reason: "missing_ts" };
  const body = buildThreadMarkerCommentBody({ threadKey, channel, ts });
  const current = comments || (await listIssueComments({ github, owner, repo, issueNumber }));
  const existing = current.find((comment) =>
    extractThreadMarkers(comment.body || "").some((marker) => marker.key === threadKey),
  );
  if (dryRun) return { ok: true, dryRun: true, action: existing ? "update" : "create" };
  if (existing) {
    await github.rest.issues.updateComment({
      owner,
      repo,
      comment_id: existing.id,
      body,
    });
    return { ok: true, action: "update", commentId: existing.id };
  }
  const { data } = await github.rest.issues.createComment({
    owner,
    repo,
    issue_number: issueNumber,
    body,
  });
  return { ok: true, action: "create", commentId: data.id };
}

async function postSlackMessage({ token, channel, text, threadTs, replyBroadcast, dryRun, fetchImpl }) {
  const slackToken = nonEmpty(token);
  const slackChannel = nonEmpty(channel);
  if (!slackToken || !slackChannel) {
    return { ok: false, skipped: true, error: "missing_slack_config" };
  }
  const payload = {
    channel: slackChannel,
    text: nonEmpty(text),
    mrkdwn: true,
    unfurl_links: false,
    unfurl_media: false,
  };
  if (threadTs) payload.thread_ts = threadTs;
  if (replyBroadcast && threadTs) payload.reply_broadcast = true;
  if (dryRun) return { ok: true, dryRun: true, channel: slackChannel, ts: "dry-run" };

  const send = fetchImpl || global.fetch;
  if (typeof send !== "function") {
    return { ok: false, error: "fetch_unavailable" };
  }

  try {
    const response = await send(SLACK_POST_MESSAGE_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${slackToken}`,
        "Content-Type": "application/json; charset=utf-8",
      },
      body: JSON.stringify(payload),
    });
    let data = {};
    try {
      data = await response.json();
    } catch {
      data = {};
    }
    return {
      ok: Boolean(data.ok),
      status: response.status,
      channel: data.channel || slackChannel,
      ts: data.ts || "",
      error: data.ok ? "" : data.error || `http_${response.status}`,
    };
  } catch (error) {
    return { ok: false, error: nonEmpty(error.message) || "slack_request_failed" };
  }
}

function relatedIssueNumber(prBody) {
  const text = String(prBody || "");
  const related = /Related to\s+#(\d+)/i.exec(text);
  if (related) return Number(related[1]);
  const closes = /\b(Closes|Close|Closed|Fixes|Fix)\s+#(\d+)/i.exec(text);
  if (closes) return Number(closes[2]);
  return 0;
}

function normalizeKnownReviewToken(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  const lowered = text.toLowerCase();
  for (const item of KNOWN_REVIEW_RESULTS) {
    if (lowered === item) return item;
  }
  if (text.includes("Human Reviewへ進行可")) return "approve_for_human_review";
  if (text.includes("修正後に再AI Review")) return "request_changes";
  if (text.includes("Human判断待ち")) return "needs_human_decision";
  return "";
}

function normalizeReviewResult(value) {
  const direct = normalizeKnownReviewToken(value);
  if (direct) return direct;
  const text = String(value || "");
  for (const item of KNOWN_REVIEW_RESULTS) {
    if (text.includes(item)) return item;
  }
  if (text.includes("Human Reviewへ進行可")) return "approve_for_human_review";
  if (text.includes("修正後に再AI Review")) return "request_changes";
  if (text.includes("Human判断待ち")) return "needs_human_decision";
  return "";
}

function isAutomationBypassComment(body) {
  const text = String(body || "").trimStart();
  if (text.startsWith(AUTOMATION_STATUS_COMMENT_PREFIX)) return true;
  if (text.includes(SLACK_THREAD_MARKER_NOTE)) return true;
  if (text.includes(`<!-- ${MARKER_PREFIX}`)) return true;
  return false;
}

function hasAiReviewResultHeading(body) {
  const text = String(body || "");
  return text.includes(AI_REVIEW_HEADING_1) || text.includes(AI_REVIEW_HEADING_22);
}

function hasReviewResultTableRow(body) {
  return /\|\s*Review Result\s*\|/i.test(String(body || ""));
}

function isAiReviewResultComment(body) {
  if (isAutomationBypassComment(body)) return false;
  const text = String(body || "");
  if (hasAiReviewResultHeading(text)) return true;
  if (!hasReviewResultTableRow(text)) return false;
  return Boolean(extractReviewResultTableCell(text));
}

function extractReviewResultTableCell(body) {
  const text = String(body || "");
  const backtick = /\|\s*Review Result\s*\|\s*`([^`]+)`\s*\|/i.exec(text);
  if (backtick) return normalizeKnownReviewToken(backtick[1]);
  const plain = /\|\s*Review Result\s*\|\s*([^\n|]+?)\s*\|/i.exec(text);
  if (plain) return normalizeKnownReviewToken(plain[1]);
  return "";
}

function extractReviewResultClassification(body) {
  const text = String(body || "");
  const match =
    /###\s*レビュー結果分類\s*\r?\n\s*(?:```[^\n]*\r?\n)?\s*`?(approve_for_human_review|request_changes|needs_human_decision|split_required|blocked)`?/i.exec(
      text,
    );
  if (!match) return "";
  return normalizeKnownReviewToken(match[1]);
}

function extractReviewResultFromAiComment(body) {
  if (!isAiReviewResultComment(body)) {
    return { ok: false, reason: "not_ai_review_comment" };
  }
  const candidates = [];
  const table = extractReviewResultTableCell(body);
  if (table) candidates.push(table);
  const classification = extractReviewResultClassification(body);
  if (classification) candidates.push(classification);
  const unique = [...new Set(candidates.filter(Boolean))];
  if (unique.length === 1) return { ok: true, value: unique[0] };
  if (unique.length > 1) return { ok: false, reason: "ambiguous_review_result" };
  return { ok: false, reason: "review_result_not_found" };
}

function statusNamesEqual(a, b) {
  return nonEmpty(a).toLowerCase() === nonEmpty(b).toLowerCase();
}

function expectedCurrentStatusForAiReview(reviewResult) {
  const normalized = normalizeKnownReviewToken(reviewResult);
  if (!normalized) return "";
  return "AI Review";
}

function expectedCurrentStatusForHumanReview() {
  return "Human Review";
}

function buildStatusSyncConfirmationComment({ taskIssueNumber, nextStatus }) {
  return `Project Status更新意図: Issue #${taskIssueNumber} を \`${nextStatus}\` へ更新しました。`;
}

function reviewResultLabelForHumans(reviewResult) {
  const normalized = normalizeKnownReviewToken(reviewResult);
  if (normalized === "approve_for_human_review") return "Human Reviewへ進行可";
  if (normalized === "request_changes") return "修正後に再AI Review";
  if (normalized === "needs_human_decision") return "Human判断待ち";
  if (normalized === "split_required") return "split_required";
  if (normalized === "blocked") return "blocked";
  return normalized || "不明";
}

function statusFromReviewResult(result, body) {
  const normalized = normalizeReviewResult(result);
  if (normalized === "approve_for_human_review") return "Human Review";
  if (normalized === "needs_human_decision") {
    if (/次Status\s*\|\s*`?In Progress`?/i.test(String(body || ""))) return "In Progress";
    return "Human Review";
  }
  if (["request_changes", "split_required", "blocked"].includes(normalized)) return "In Progress";
  return "";
}

function notificationLevelFromReviewResult(result) {
  const normalized = normalizeReviewResult(result);
  if (normalized === "approve_for_human_review") return "review";
  if (normalized === "split_required") return "warning";
  if (normalized === "blocked") return "error";
  if (["request_changes", "needs_human_decision"].includes(normalized)) return "action_required";
  return "info";
}

module.exports = {
  MARKER_PREFIX,
  AI_REVIEW_HEADING_1,
  AI_REVIEW_HEADING_22,
  AUTOMATION_STATUS_COMMENT_PREFIX,
  KNOWN_REVIEW_RESULTS,
  buildSlackText,
  buildThreadKey,
  buildThreadMarker,
  extractThreadMarkers,
  findThreadTsFromComments,
  buildThreadMarkerCommentBody,
  listIssueComments,
  upsertThreadMarkerComment,
  postSlackMessage,
  relatedIssueNumber,
  normalizeKnownReviewToken,
  normalizeReviewResult,
  isAutomationBypassComment,
  isAiReviewResultComment,
  extractReviewResultFromAiComment,
  statusNamesEqual,
  expectedCurrentStatusForAiReview,
  expectedCurrentStatusForHumanReview,
  buildStatusSyncConfirmationComment,
  reviewResultLabelForHumans,
  statusFromReviewResult,
  notificationLevelFromReviewResult,
};

