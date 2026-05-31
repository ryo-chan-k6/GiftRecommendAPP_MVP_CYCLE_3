"use strict";

const fs = require("fs");
const slack = require("./slack-notify.cjs");
const publish = require("./publish-ai-review-and-dispatch.cjs");

const LOG_LINE_PREFIX_RE = /^\d{4}-\d{2}-\d{2}T[^\s]+\s+/;
const TRANSCRIPT_STOP_RE = /^---$|^### \d+\./;

function nonEmpty(value) {
  return String(value || "").trim();
}

function stripLogPrefix(line) {
  return String(line || "").replace(LOG_LINE_PREFIX_RE, "");
}

function extractAiReviewCommentBlocks(transcript) {
  const lines = String(transcript || "").split(/\r?\n/);
  const stripped = lines.map(stripLogPrefix);
  const blocks = [];

  for (let idx = 0; idx < stripped.length; idx += 1) {
    if (stripped[idx].trim() !== "# AI Review Result") continue;

    const block = [];
    for (let i = idx; i < stripped.length; i += 1) {
      const line = stripped[i];
      if (
        i > idx &&
        (TRANSCRIPT_STOP_RE.test(line.trim()) ||
          line.includes("publish-ai-review-and-dispatch.cjs") ||
          line.includes("publish-ai-review-harness-fallback.cjs"))
      ) {
        break;
      }
      block.push(line);
    }

    const body = block.join("\n").trim();
    if (slack.isAiReviewResultComment(body)) {
      blocks.push(body);
    }
  }

  return blocks;
}

function extractLatestAiReviewCommentFromTranscript(transcript) {
  const blocks = extractAiReviewCommentBlocks(transcript);
  return blocks.length ? blocks[blocks.length - 1] : "";
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

function extractLatestAiReviewCommentFromSources({ transcriptText, transcriptPath, resultJsonPath }) {
  const transcript =
    nonEmpty(transcriptText) ||
    (transcriptPath && fs.existsSync(transcriptPath)
      ? fs.readFileSync(transcriptPath, "utf8")
      : "");
  const resultText = readResultTextFromJson(resultJsonPath);
  const combined = [transcript, resultText].filter(Boolean).join("\n");
  return extractLatestAiReviewCommentFromTranscript(combined);
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
  extractAiReviewCommentBlocks,
  extractLatestAiReviewCommentFromTranscript,
  extractLatestAiReviewCommentFromSources,
  readResultTextFromJson,
  publishAiReviewHarnessFallback,
};
