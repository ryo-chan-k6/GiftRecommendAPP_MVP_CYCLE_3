"use strict";

const fs = require("fs");
const slack = require("./slack-notify.cjs");
const publish = require("./publish-fix-complete-and-dispatch.cjs");
const fixTaskPrIssueReference = require("./fix-task-pr-issue-reference.cjs");

const LOG_LINE_PREFIX_RE = /^\d{4}-\d{2}-\d{2}T[^\s]+\s+/;
// review-pr fallback と同型（`^## \d+\.` は使わない）。§12 境界のみ ## で止める。
const TRANSCRIPT_STOP_RE = /^---$|^### \d+\.|^## 12\./;
const FIX_COMPLETE_TITLE = slack.FIX_COMPLETE_TITLE;
const FIX_COMMAND_RESULT_HEADING = "## fix-review-comments 実行結果";

function nonEmpty(value) {
  return String(value || "").trim();
}

function stripLogPrefix(line) {
  return String(line || "").replace(LOG_LINE_PREFIX_RE, "");
}

function isValidFixCompleteCommentBody(body) {
  return Boolean(body) && slack.isFixCompleteResultComment(body);
}

function ensureFixCompleteTitle(body) {
  const text = String(body || "").trim();
  if (!text) return "";
  if (text.includes(FIX_COMPLETE_TITLE)) return text;
  return `${FIX_COMPLETE_TITLE}\n\n${text}`;
}

function extractBlockFromStart(stripped, startIdx) {
  const block = [];
  for (let i = startIdx; i < stripped.length; i += 1) {
    const line = stripped[i];
    if (
      i > startIdx &&
      (TRANSCRIPT_STOP_RE.test(line.trim()) ||
        line.includes("publish-fix-complete-and-dispatch.cjs") ||
        line.includes("publish-fix-complete-harness-fallback.cjs"))
    ) {
      break;
    }
    block.push(line);
  }
  return block.join("\n").trim();
}

function extractFixCompleteCommentBlocks(transcript) {
  const lines = String(transcript || "").split(/\r?\n/);
  const stripped = lines.map(stripLogPrefix);
  const blocks = [];
  const startHeadings = [
    FIX_COMPLETE_TITLE,
    FIX_COMMAND_RESULT_HEADING,
    slack.FIX_COMPLETE_HEADING_1,
  ];

  for (let idx = 0; idx < stripped.length; idx += 1) {
    const trimmed = stripped[idx].trim();
    if (!startHeadings.some((heading) => trimmed === heading || trimmed.startsWith(heading))) {
      continue;
    }
    const body = ensureFixCompleteTitle(extractBlockFromStart(stripped, idx));
    if (isValidFixCompleteCommentBody(body)) {
      blocks.push(body);
    }
  }

  return blocks;
}

function extractFixOutcomeFromProse(text) {
  const normalized = String(text || "");
  const sectionMatch = /###\s*Fix Outcome\s*\n+\s*`?([^\n`]+)`?/i.exec(normalized);
  if (sectionMatch) {
    return slack.normalizeKnownFixOutcome(sectionMatch[1]);
  }
  const tableOutcome = slack.extractFixOutcomeTableCell(normalized);
  if (tableOutcome) return tableOutcome;

  const found = new Set();
  for (const item of slack.KNOWN_FIX_OUTCOMES || []) {
    if (new RegExp(`\\b${item}\\b`).test(normalized)) {
      found.add(item);
    }
  }
  if (found.size === 1) return [...found][0];
  return "";
}

function synthesizeFixCompleteComment({ fixOutcome, prNumber }) {
  const outcome = slack.normalizeKnownFixOutcome(fixOutcome);
  if (!outcome) return "";
  const prLabel = prNumber ? `#${Number(prNumber)}` : "-";
  const body = `${FIX_COMPLETE_TITLE}

## 1. 対応結果

| 項目 | 内容 |
| ---- | ---- |
| Fix Outcome | \`${outcome}\` |
| 対象PR | \`${prLabel}\` |

## 12. Status更新意図

| 項目 | 内容 |
| ---- | ---- |
| 次Status | \`AI Review\` |

<!-- harness-fallback: synthesized from agent transcript -->
`;
  return isValidFixCompleteCommentBody(body) ? body : "";
}

function extractLatestFixCompleteCommentFromTranscript(transcript, { prNumber } = {}) {
  const blocks = extractFixCompleteCommentBlocks(transcript);
  const usableBlocks = blocks.filter((block) => {
    const extracted = slack.extractFixOutcomeFromComment(block);
    return extracted.ok;
  });
  if (usableBlocks.length) return usableBlocks[usableBlocks.length - 1];

  const uniqueOutcomes = new Set();
  const proseOutcome = extractFixOutcomeFromProse(transcript);
  if (proseOutcome) uniqueOutcomes.add(proseOutcome);

  if (uniqueOutcomes.size === 1) {
    return synthesizeFixCompleteComment({
      fixOutcome: [...uniqueOutcomes][0],
      prNumber,
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

function extractLatestFixCompleteCommentFromSources({
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
  return extractLatestFixCompleteCommentFromTranscript(combined, { prNumber });
}

async function publishFixCompleteHarnessFallback({
  owner,
  repo,
  repository,
  prNumber,
  transcriptPath,
  transcriptText,
  resultJsonPath,
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

  const verify = await publish.verifyFixCompleteDispatch({
    owner: resolvedRepo.owner,
    repo: resolvedRepo.repo,
    prNumber,
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
      message: "Transcript is empty; cannot extract fix-complete comment.",
      prior_verify: verify,
    };
  }

  const commentBody = extractLatestFixCompleteCommentFromSources({
    transcriptText: transcript,
    transcriptPath: "",
    resultJsonPath,
    prNumber,
  });
  if (!commentBody) {
    return {
      ok: false,
      reason: "no_comment_in_transcript",
      message: "No valid fix-complete comment block found in harness transcript.",
      prior_verify: verify,
    };
  }

  const extracted = slack.extractFixOutcomeFromComment(commentBody);
  if (!extracted.ok || extracted.value !== "ready_for_ai_review") {
    return {
      ok: true,
      skipped: true,
      reason: "fix_outcome_not_ready_for_ai_review",
      fix_outcome: extracted.ok ? extracted.value : "",
      prior_verify: verify,
    };
  }

  let prBodyFix = null;
  try {
    prBodyFix = await fixTaskPrIssueReference.fixTaskPrIssueReference({
      owner: resolvedRepo.owner,
      repo: resolvedRepo.repo,
      prNumber,
      token: authToken,
      dryRun,
      fetchImpl,
    });
  } catch (error) {
    return {
      ok: false,
      reason: "pr_body_fix_failed",
      message: error && error.message ? error.message : String(error),
      prior_verify: verify,
    };
  }

  const publishResult = await publish.publishFixCompleteAndDispatch({
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
    pr_body_fix: prBodyFix,
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
  node .github/scripts/publish-fix-complete-harness-fallback.cjs \\
    --repository owner/repo \\
    --pr <number> \\
    --transcript /path/to/definition-run-transcript.log \\
    [--result-json /path/to/definition-run-result.json] \\
    [--dry-run]

Publishes fix-complete comment + fix-ready dispatch when Cloud Agent cannot use GH_BOT_TOKEN.
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

  const result = await publishFixCompleteHarnessFallback(options);
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
  FIX_COMMAND_RESULT_HEADING,
  extractFixCompleteCommentBlocks,
  extractFixOutcomeFromProse,
  synthesizeFixCompleteComment,
  extractLatestFixCompleteCommentFromTranscript,
  extractLatestFixCompleteCommentFromSources,
  readResultTextFromJson,
  publishFixCompleteHarnessFallback,
};
