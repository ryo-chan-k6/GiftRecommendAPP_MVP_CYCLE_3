"use strict";

const MARKER_PREFIX = "slack-thread:v1";
const SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage";

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

function normalizeReviewResult(value) {
  const text = String(value || "");
  const known = [
    "approve_for_human_review",
    "request_changes",
    "needs_human_decision",
    "split_required",
    "blocked",
  ];
  for (const item of known) {
    if (text.includes(item)) return item;
  }
  if (text.includes("Human Reviewへ進行可")) return "approve_for_human_review";
  if (text.includes("修正後に再AI Review")) return "request_changes";
  if (text.includes("Human判断待ち")) return "needs_human_decision";
  return "";
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
  normalizeReviewResult,
  statusFromReviewResult,
  notificationLevelFromReviewResult,
};

