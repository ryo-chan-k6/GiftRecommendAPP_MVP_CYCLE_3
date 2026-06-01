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

function synthesizeAiReviewComment({ reviewResult, prNumber }) {
  const token = slack.normalizeReviewResult(reviewResult);
  if (!token) return "";
  const nextStatus = slack.statusFromReviewResult(token, "") || "Human Review";
  const prLabel = prNumber ? `#${Number(prNumber)}` : "-";
  const body = `# AI Review Result

## 1. レビュー結果

| 項目          | 内容                     |
| ------------- | ------------------------ |
| Review Result | \`${token}\` |
| 対象PR        | \`${prLabel}\` |

## 22. Status更新意図

| 次Status   | \`${nextStatus}\` |

<!-- harness-fallback: synthesized from agent transcript -->
`;
  return isValidAiReviewCommentBody(body) ? body : "";
}

function extractLatestAiReviewCommentFromTranscript(transcript, { prNumber } = {}) {
  const blocks = extractAiReviewCommentBlocks(transcript);
  if (blocks.length) return blocks[blocks.length - 1];

  const unique = collectUniqueReviewResults(transcript);
  if (unique.length === 1) {
    return synthesizeAiReviewComment({ reviewResult: unique[0], prNumber });
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
  synthesizeAiReviewComment,
  extractAiReviewCommentBlocks,
  extractLatestAiReviewCommentFromTranscript,
  extractLatestAiReviewCommentFromSources,
  readResultTextFromJson,
  publishAiReviewHarnessFallback,
};
