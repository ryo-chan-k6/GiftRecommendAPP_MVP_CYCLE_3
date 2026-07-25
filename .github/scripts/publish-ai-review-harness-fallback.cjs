"use strict";

const fs = require("fs");
const slack = require("./slack-notify.cjs");
const publish = require("./publish-ai-review-and-dispatch.cjs");

const LOG_LINE_PREFIX_RE = /^\d{4}-\d{2}-\d{2}T[^\s]+\s+/;
const TRANSCRIPT_STOP_RE = /^---$|^### \d+\./;
const REVIEW_SECTION_HEADING = slack.AI_REVIEW_HEADING_1;

function nonEmpty(value) {
  return String(value || "").trim();
}

function stripLogPrefix(line) {
  return String(line || "").replace(LOG_LINE_PREFIX_RE, "");
}

function isValidAiReviewCommentBody(body) {
  return Boolean(body) && slack.isAiReviewResultComment(body);
}

function ensureAiReviewResultHeading(body) {
  const text = String(body || "").trim();
  if (!text) return "";
  if (text.includes("# AI Review Result")) return text;
  return `# AI Review Result\n\n${text}`;
}

function extractBlockFromStart(stripped, startIdx) {
  const block = [];
  for (let i = startIdx; i < stripped.length; i += 1) {
    const line = stripped[i];
    if (
      i > startIdx &&
      (TRANSCRIPT_STOP_RE.test(line.trim()) ||
        line.includes("publish-ai-review-and-dispatch.cjs") ||
        line.includes("publish-ai-review-harness-fallback.cjs"))
    ) {
      break;
    }
    block.push(line);
  }
  return block.join("\n").trim();
}

function extractAiReviewCommentBlocks(transcript) {
  const lines = String(transcript || "").split(/\r?\n/);
  const stripped = lines.map(stripLogPrefix);
  const blocks = [];

  for (let idx = 0; idx < stripped.length; idx += 1) {
    const trimmed = stripped[idx].trim();
    if (trimmed !== "# AI Review Result" && trimmed !== REVIEW_SECTION_HEADING) continue;

    if (trimmed === REVIEW_SECTION_HEADING) {
      const lookback = stripped.slice(Math.max(0, idx - 5), idx).map((line) => line.trim());
      if (lookback.includes("# AI Review Result")) continue;
    }

    const body = ensureAiReviewResultHeading(extractBlockFromStart(stripped, idx));
    if (isValidAiReviewCommentBody(body)) {
      blocks.push(body);
    }
  }

  return blocks;
}

function collectUniqueReviewResults(text) {
  const found = new Set();
  const normalized = String(text || "");

  const tableRe = /\|\s*Review Result\s*\|\s*`?([^|\n`]+)`?\s*\|/gi;
  let match;
  while ((match = tableRe.exec(normalized)) !== null) {
    const token = slack.normalizeReviewResult(match[1]);
    if (token) found.add(token);
  }

  for (const item of slack.KNOWN_REVIEW_RESULTS) {
    if (new RegExp(`\\b${item}\\b`).test(normalized)) {
      found.add(item);
    }
  }

  const prose = slack.normalizeReviewResult(normalized);
  if (prose) found.add(prose);

  return [...found];
}

function formatNgReasonSummarySection(items, { maxItems = publish.MAX_NG_REASON_SUMMARY_ITEMS } = {}) {
  const list = Array.isArray(items) ? items.filter(Boolean) : [];
  if (!list.length) return "なし";
  const limit = Number.isFinite(maxItems) ? Math.max(1, maxItems) : 10;
  const lines = list.slice(0, limit).map((item) => {
    if (typeof item === "string") return `- ${item}`;
    const title = nonEmpty(item.title) || "指摘";
    const target = nonEmpty(item.target) || "-";
    const reason = nonEmpty(item.reason) || nonEmpty(item.description) || "-";
    return `- **${title}** / 対象: \`${target}\` / 理由: ${reason}`;
  });
  if (list.length > limit) {
    lines.push(`- 他${list.length - limit}件は §7 参照`);
  }
  return lines.join("\n");
}

function extractMustFixSummariesFromTranscript(transcript, { maxItems = publish.MAX_NG_REASON_SUMMARY_ITEMS } = {}) {
  const text = String(transcript || "");
  if (!text.trim()) return [];
  const items = [];
  const seen = new Set();

  // §7 修正必須ブロック: ### 7.N title + 対象 / 理由 テーブル
  const sectionMatch = /##\s*7\.\s*修正必須事項([\s\S]*?)(?=\n##\s*\d+\.|\n#\s|$)/i.exec(text);
  const section = sectionMatch ? sectionMatch[1] : text;
  const blockRe = /###\s*7\.\d+\s+([^\n]+)([\s\S]*?)(?=\n###\s*7\.|\n##\s*\d+\.|\n#\s|$)/gi;
  let block;
  while ((block = blockRe.exec(section)) !== null) {
    const title = nonEmpty(block[1]);
    const body = block[2] || "";
    const target =
      nonEmpty((/\|\s*対象\s*\|\s*`?([^|\n`]+)`?\s*\|/i.exec(body) || [])[1]) ||
      nonEmpty((/\|\s*対象\s*\|\s*([^|\n]+)\|/i.exec(body) || [])[1]) ||
      "-";
    const reason =
      nonEmpty((/####\s*理由\s*\n+([\s\S]*?)(?=\n####|\n###|\n##|$)/i.exec(body) || [])[1]) ||
      nonEmpty((/\|\s*対応方針\s*\|\s*`?([^|\n`]+)`?\s*\|/i.exec(body) || [])[1]) ||
      nonEmpty((/####\s*指摘内容\s*\n+([\s\S]*?)(?=\n####|\n###|\n##|$)/i.exec(body) || [])[1]) ||
      "-";
    const severity = nonEmpty((/\|\s*重要度\s*\|\s*`?([^|\n`]+)`?\s*\|/i.exec(body) || [])[1]);
    if (severity && !/must/i.test(severity)) continue;
    const key = `${title}|${target}|${reason}`;
    if (!title || seen.has(key)) continue;
    seen.add(key);
    items.push({
      title,
      target: target.replace(/\s+/g, " ").trim(),
      reason: reason.replace(/\s+/g, " ").trim().slice(0, 200),
    });
    if (items.length >= maxItems * 2) break;
  }

  // 既存の NG理由サマリ箇条書きがあれば流用
  if (!items.length) {
    const ngSection = publish.extractNgReasonSummarySection(text);
    for (const line of ngSection.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!/^[-*]\s+/.test(trimmed) || /^[-*]\s*なし\s*$/.test(trimmed)) continue;
      const bullet = trimmed.replace(/^[-*]\s+/, "").trim();
      if (!bullet || seen.has(bullet)) continue;
      seen.add(bullet);
      items.push(bullet);
      if (items.length >= maxItems * 2) break;
    }
  }

  // 「修正必須」近傍の箇条書き（must 明示または見出し近傍）
  if (!items.length) {
    const bulletRe = /^[-*]\s+(?:\*\*)?(.+?)(?:\*\*)?\s*(?:\/\s*対象[:：]\s*`?([^`/\n]+)`?)?\s*(?:\/\s*理由[:：]\s*(.+))?$/gm;
    let m;
    while ((m = bulletRe.exec(text)) !== null) {
      const title = nonEmpty(m[1]);
      if (!title || /任意改善|良い点|確認した事実/.test(title)) continue;
      const nearby = text.slice(Math.max(0, m.index - 80), m.index);
      if (!/修正必須|must|NG理由/i.test(nearby) && !/must/i.test(title)) continue;
      const key = title;
      if (seen.has(key)) continue;
      seen.add(key);
      items.push({
        title,
        target: nonEmpty(m[2]) || "-",
        reason: nonEmpty(m[3]) || "-",
      });
      if (items.length >= maxItems * 2) break;
    }
  }

  return items.slice(0, maxItems * 2);
}

function synthesizeAiReviewComment({ reviewResult, prNumber, transcript }) {
  const token = slack.normalizeReviewResult(reviewResult);
  if (!token) return "";
  const nextStatus = slack.statusFromReviewResult(token, "") || "Human Review";
  const prLabel = prNumber ? `#${Number(prNumber)}` : "-";
  const needsNg = publish.requiresNgReasonSummary(token);
  const summaries = needsNg ? extractMustFixSummariesFromTranscript(transcript || "") : [];
  const ngBody = needsNg
    ? formatNgReasonSummarySection(summaries)
    : "なし";
  const body = `# AI Review Result

## 1. レビュー結果

| 項目          | 内容                     |
| ------------- | ------------------------ |
| Review Result | \`${token}\` |
| 対象PR        | \`${prLabel}\` |

## NG理由サマリ

${ngBody}

## 22. Status更新意図

| 次Status   | \`${nextStatus}\` |

<!-- harness-fallback: synthesized from agent transcript -->
`;
  return isValidAiReviewCommentBody(body) ? body : "";
}

function extractLatestAiReviewCommentFromTranscript(transcript, { prNumber } = {}) {
  const blocks = extractAiReviewCommentBlocks(transcript);
  // 切り詰め（本文退避・省略）ブロックは投稿せず、合成フォールバックへ回す。
  const usableBlocks = blocks.filter((block) => !publish.isTruncatedAiReviewComment(block));
  if (usableBlocks.length) return usableBlocks[usableBlocks.length - 1];

  const unique = collectUniqueReviewResults(transcript);
  if (unique.length === 1) {
    return synthesizeAiReviewComment({
      reviewResult: unique[0],
      prNumber,
      transcript,
    });
  }
  return "";
}

function readResultTextFromJson(resultJsonPath) {
  const filePath = nonEmpty(resultJsonPath);
  if (!filePath || !fs.existsSync(filePath)) return "";
  try {
    const parsed = JSON.parse(fs.readFileSync(filePath, "utf8"));
    return nonEmpty(parsed && parsed.result);
  } catch {
    return "";
  }
}

function extractLatestAiReviewCommentFromSources({
  transcriptText,
  transcriptPath,
  resultJsonPath,
  prNumber,
}) {
  const transcript =
    nonEmpty(transcriptText) ||
    (transcriptPath && fs.existsSync(transcriptPath)
      ? fs.readFileSync(transcriptPath, "utf8")
      : "");
  const resultText = readResultTextFromJson(resultJsonPath);
  const combined = [transcript, resultText].filter(Boolean).join("\n");
  return extractLatestAiReviewCommentFromTranscript(combined, { prNumber });
}

async function publishAiReviewHarnessFallback({
  owner,
  repo,
  repository,
  prNumber,
  transcriptPath,
  transcriptText,
  resultJsonPath,
  sinceIso,
  token,
  dryRun,
  fetchImpl,
}) {
  const resolvedRepo = repository
    ? { owner: repository.split("/")[0], repo: repository.split("/")[1] }
    : { owner, repo };
  const authToken = nonEmpty(token) || nonEmpty(process.env.GH_BOT_TOKEN);
  if (!authToken) {
    throw new Error("GH_BOT_TOKEN is required for harness publish fallback");
  }
  if (!prNumber) {
    throw new Error("prNumber is required");
  }

  const verify = await publish.verifyAiReviewDispatch({
    owner: resolvedRepo.owner,
    repo: resolvedRepo.repo,
    prNumber,
    sinceIso,
    token: authToken,
    fetchImpl,
  });
  if (verify.ok) {
    return {
      ok: true,
      skipped: true,
      reason: "already_published",
      verify,
    };
  }

  const transcript =
    nonEmpty(transcriptText) ||
    (transcriptPath && fs.existsSync(transcriptPath)
      ? fs.readFileSync(transcriptPath, "utf8")
      : "");
  if (!transcript && !readResultTextFromJson(resultJsonPath)) {
    return {
      ok: false,
      reason: "transcript_missing",
      message: "Transcript is empty; cannot extract AI Review comment.",
      prior_verify: verify,
    };
  }

  const commentBody = extractLatestAiReviewCommentFromSources({
    transcriptText: transcript,
    transcriptPath: "",
    resultJsonPath,
    prNumber,
  });
  if (!commentBody) {
    return {
      ok: false,
      reason: "no_comment_in_transcript",
      message: "No valid AI Review comment block found in harness transcript.",
      prior_verify: verify,
    };
  }
  if (publish.isMissingNgReasonSummary(commentBody)) {
    return {
      ok: false,
      reason: "ng_reason_summary_missing",
      message:
        "AI Review comment is missing required ## NG理由サマリ for non-approve result. " +
        "Ensure must-level fix summaries are present in the agent transcript or comment body.",
      prior_verify: verify,
      synthesized: commentBody.includes("harness-fallback: synthesized"),
    };
  }

  const publishResult = await publish.publishAiReviewAndDispatch({
    owner: resolvedRepo.owner,
    repo: resolvedRepo.repo,
    prNumber,
    commentBody,
    token: authToken,
    dryRun,
    fetchImpl,
  });

  return {
    ok: true,
    skipped: false,
    reason: "published",
    synthesized: commentBody.includes("harness-fallback: synthesized"),
    prior_verify: verify,
    publish: publishResult,
  };
}

function parseCliArgs(argv) {
  const args = argv.slice(2);
  const options = {
    owner: "",
    repo: "",
    repository: "",
    prNumber: "",
    transcriptPath: "",
    sinceIso: "",
    resultJsonPath: "",
    dryRun: false,
  };
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--dry-run") {
      options.dryRun = true;
      continue;
    }
    if (arg === "--repository" || arg === "-R") {
      options.repository = args[++i] || "";
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
    if (arg === "--pr" || arg === "--pr-number") {
      options.prNumber = args[++i] || "";
      continue;
    }
    if (arg === "--transcript") {
      options.transcriptPath = args[++i] || "";
      continue;
    }
    if (arg === "--since" || arg === "--since-iso") {
      options.sinceIso = args[++i] || "";
      continue;
    }
    if (arg === "--result-json") {
      options.resultJsonPath = args[++i] || "";
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
  node .github/scripts/publish-ai-review-harness-fallback.cjs \\
    --repository owner/repo \\
    --pr <number> \\
    --transcript /path/to/definition-run-transcript.log \\
    [--since <harness-started-at-iso>] \\
    [--result-json /path/to/definition-run-result.json] \\
    [--dry-run]

Publishes AI Review comment + status-sync when Cloud Agent cannot use GH_BOT_TOKEN.
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

  const result = await publishAiReviewHarnessFallback(options);
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  if (!result.ok) process.exitCode = 1;
}

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = {
  LOG_LINE_PREFIX_RE,
  REVIEW_SECTION_HEADING,
  collectUniqueReviewResults,
  formatNgReasonSummarySection,
  extractMustFixSummariesFromTranscript,
  synthesizeAiReviewComment,
  extractAiReviewCommentBlocks,
  extractLatestAiReviewCommentFromTranscript,
  extractLatestAiReviewCommentFromSources,
  readResultTextFromJson,
  publishAiReviewHarnessFallback,
};
