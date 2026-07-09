#!/usr/bin/env node
/**
 * Layer2 レコメンド品質評価ランナー（Epic C C4 / テスト定義書 §9.7）。
 * 固定評価ケースを読み込み、自動メトリクスを算出し artifact 用 JSON / Markdown を出力する。
 * Phase4b 前は skeleton モード（mock パイプライン結果）を正とする。
 */

import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../..");

const CASES_PATH = path.join(REPO_ROOT, "tests/fixtures/evaluation/cases.json");
const MOCK_RESULTS_DIR = path.join(
  REPO_ROOT,
  "tests/fixtures/evaluation/mock-results",
);

function parseArgs(argv) {
  const options = {
    pipelineMode: process.env.PIPELINE_MODE ?? "skeleton",
    openaiMode: process.env.OPENAI_MODE ?? "mock",
    outputDir: path.join(REPO_ROOT, "tests/recommendation-quality/output"),
    recoBaseUrl: process.env.RECO_BASE_URL ?? "",
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--pipeline-mode") {
      options.pipelineMode = argv[index + 1] ?? options.pipelineMode;
      index += 1;
    } else if (arg === "--openai-mode") {
      options.openaiMode = argv[index + 1] ?? options.openaiMode;
      index += 1;
    } else if (arg === "--output-dir") {
      options.outputDir = path.resolve(argv[index + 1] ?? options.outputDir);
      index += 1;
    } else if (arg === "--reco-base-url") {
      options.recoBaseUrl = argv[index + 1] ?? options.recoBaseUrl;
      index += 1;
    }
  }

  return options;
}

async function readJson(relativePath) {
  const absolutePath = path.isAbsolute(relativePath)
    ? relativePath
    : path.join(REPO_ROOT, relativePath);
  const raw = await readFile(absolutePath, "utf8");
  return JSON.parse(raw);
}

function includesNgKeyword(text, keywords) {
  if (!keywords?.length) {
    return false;
  }
  const normalized = String(text ?? "").toLowerCase();
  return keywords.some((keyword) =>
    normalized.includes(String(keyword).toLowerCase()),
  );
}

function computeBudgetCompliance(resultItems, budgetMin, budgetMax) {
  if (!resultItems.length) {
    return {
      metric: "budget_compliance",
      pass: false,
      detail: "result_items_empty",
    };
  }

  const violations = resultItems.filter((item) => {
    const price = Number(item.price);
    if (Number.isNaN(price)) {
      return true;
    }
    if (budgetMin != null && price < budgetMin) {
      return true;
    }
    if (budgetMax != null && price > budgetMax) {
      return true;
    }
    return false;
  });

  return {
    metric: "budget_compliance",
    pass: violations.length === 0,
    detail:
      violations.length === 0
        ? "all_items_within_budget"
        : `violations=${violations.map((item) => item.itemId).join(",")}`,
  };
}

function computeNgAvoidance(resultItems, ngKeywords) {
  const hits = resultItems.filter((item) =>
    includesNgKeyword(item.label, ngKeywords),
  );

  return {
    metric: "ng_avoidance",
    pass: hits.length === 0,
    detail:
      hits.length === 0
        ? "no_ng_keyword_hits"
        : `hits=${hits.map((item) => item.itemId).join(",")}`,
  };
}

function computeTop1FormalityScore(resultItems) {
  const top1 = resultItems.find((item) => item.rank === 1) ?? resultItems[0];
  const score = top1?.features?.formality;

  return {
    metric: "top1_formality_score",
    pass: typeof score === "number",
    value: score ?? null,
    detail: top1 ? `item=${top1.itemId}` : "missing_top1",
  };
}

function computeResultItemCount(resultItems) {
  return {
    metric: "result_item_count",
    pass: resultItems.length > 0,
    value: resultItems.length,
    detail: `count=${resultItems.length}`,
  };
}

function computeEmotionScoreDistribution(resultItems) {
  const scores = resultItems
    .map((item) => item.features?.emotion)
    .filter((value) => typeof value === "number");

  if (scores.length === 0) {
    return {
      metric: "emotion_score_distribution",
      pass: false,
      value: null,
      detail: "no_emotion_scores",
    };
  }

  const min = Math.min(...scores);
  const max = Math.max(...scores);
  const avg = scores.reduce((sum, value) => sum + value, 0) / scores.length;

  return {
    metric: "emotion_score_distribution",
    pass: true,
    value: { min, max, avg },
    detail: `min=${min.toFixed(2)},max=${max.toFixed(2)},avg=${avg.toFixed(2)}`,
  };
}

const METRIC_COMPUTERS = {
  budget_compliance: (resultItems, expected) =>
    computeBudgetCompliance(
      resultItems,
      expected.budgetMin,
      expected.budgetMax,
    ),
  ng_avoidance: (resultItems, expected) =>
    computeNgAvoidance(resultItems, expected.ngKeywords ?? []),
  top1_formality_score: (resultItems) =>
    computeTop1FormalityScore(resultItems),
  result_item_count: (resultItems) => computeResultItemCount(resultItems),
  emotion_score_distribution: (resultItems) =>
    computeEmotionScoreDistribution(resultItems),
};

async function loadPipelineResult(caseDef, options) {
  if (options.pipelineMode === "live") {
    if (!options.recoBaseUrl) {
      throw new Error(
        "live モードには RECO_BASE_URL が必要です（Phase4b 本格化後）",
      );
    }

    const healthUrl = new URL(
      "/internal/reco/v1/health",
      options.recoBaseUrl,
    ).toString();
    const response = await fetch(healthUrl);
    if (!response.ok) {
      throw new Error(`Reco health check failed: HTTP ${response.status}`);
    }

    throw new Error(
      "live パイプライン実行は Phase4b MOD-RECO/API-INT 整備後に実装予定",
    );
  }

  const mockPath = path.join(MOCK_RESULTS_DIR, `${caseDef.id}.json`);
  const mockResult = await readJson(mockPath);
  return {
    ...mockResult,
    pipelineMode: options.pipelineMode,
    openaiMode: options.openaiMode,
    source: "mock-results",
  };
}

function validateOpenAiMode(openaiMode) {
  if (openaiMode === "mock") {
    return {
      mode: "mock",
      detail: "OpenAI fixture mock（tests/fixtures/external-api/openai/）",
    };
  }

  if (openaiMode === "secrets") {
    if (!process.env.OPENAI_API_KEY) {
      throw new Error(
        "openai_mode=secrets ですが OPENAI_API_KEY が未設定です（GHA Secrets 注入を確認）",
      );
    }
    return {
      mode: "secrets",
      detail: "OPENAI_API_KEY configured via GHA Secrets",
    };
  }

  throw new Error(`unsupported openai_mode: ${openaiMode}`);
}

async function evaluateCase(caseDef, options) {
  const request = await readJson(caseDef.requestFixture);
  const pipelineResult = await loadPipelineResult(caseDef, options);
  const resultItems = pipelineResult.resultItems ?? [];

  const autoMetrics = (caseDef.autoMetrics ?? []).map((metricName) => {
    const compute = METRIC_COMPUTERS[metricName];
    if (!compute) {
      return {
        metric: metricName,
        pass: false,
        detail: "unsupported_metric",
      };
    }
    return compute(resultItems, caseDef.expectedObservations ?? {});
  });

  const structuralChecks = {
    requestFixtureExists: true,
    mockResultLoaded: pipelineResult.source === "mock-results",
    humanReviewRequired: caseDef.humanReviewRequired === true,
  };

  return {
    caseId: caseDef.id,
    title: caseDef.title,
    requestFixture: caseDef.requestFixture,
    requestSummary: {
      relationshipCode: request.relationship?.relationshipCode ?? null,
      occasionCode: request.occasion?.occasionCode ?? null,
      budgetMin: request.budget?.budgetMin ?? null,
      budgetMax: request.budget?.budgetMax ?? null,
    },
    pipeline: {
      mode: options.pipelineMode,
      openaiMode: options.openaiMode,
      source: pipelineResult.source,
    },
    resultItems,
    reason: pipelineResult.reason ?? null,
    autoMetrics,
    structuralChecks,
    humanReviewRequired: caseDef.humanReviewRequired === true,
    agentCompletionEligible:
      autoMetrics.every((metric) => metric.pass !== false) &&
      structuralChecks.requestFixtureExists,
  };
}

function buildSummaryMarkdown(report) {
  const lines = [
    "# Reco Quality Evaluation Summary",
    "",
    `| 項目 | 値 |`,
    `| --- | --- |`,
    `| runAt | ${report.runAt} |`,
    `| pipelineMode | ${report.pipelineMode} |`,
    `| openaiMode | ${report.openai.mode} |`,
    `| caseCount | ${report.cases.length} |`,
    `| autoMetricsPass | ${report.summary.autoMetricsPass}/${report.summary.autoMetricsTotal} |`,
    `| humanReviewRequired | yes（Agent 必須条件外） |`,
    "",
    "## Cases",
    "",
  ];

  for (const caseResult of report.cases) {
    lines.push(`### ${caseResult.caseId} — ${caseResult.title}`);
    lines.push("");
    lines.push(
      `- pipeline: ${caseResult.pipeline.mode} / openai: ${caseResult.pipeline.openaiMode}`,
    );
    lines.push(
      `- auto metrics: ${caseResult.autoMetrics.map((metric) => `${metric.metric}=${metric.pass ? "pass" : "fail"}`).join(", ")}`,
    );
    lines.push(
      `- human review required: ${caseResult.humanReviewRequired ? "yes" : "no"}`,
    );
    lines.push("");
  }

  lines.push("## Notes");
  lines.push("");
  lines.push(
    "- 人手評価の最終判定は Human scope（テスト定義書 §9.7.3）。本 artifact は Agent 読取用。",
  );
  lines.push(
    "- Phase4b 前は skeleton + mock-results を使用。live モードは Reco 本格実装後に有効化。",
  );

  return `${lines.join("\n")}\n`;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const openai = validateOpenAiMode(options.openaiMode);
  const casesDoc = await readJson(CASES_PATH);
  const cases = casesDoc.cases ?? [];

  if (cases.length === 0) {
    throw new Error("cases.json に評価ケースが存在しません");
  }

  const evaluatedCases = [];
  for (const caseDef of cases) {
    evaluatedCases.push(await evaluateCase(caseDef, options));
  }

  const autoMetricsTotal = evaluatedCases.reduce(
    (sum, caseResult) => sum + caseResult.autoMetrics.length,
    0,
  );
  const autoMetricsPass = evaluatedCases.reduce(
    (sum, caseResult) =>
      sum + caseResult.autoMetrics.filter((metric) => metric.pass).length,
    0,
  );

  const report = {
    schemaVersion: "1.0",
    runAt: new Date().toISOString(),
    pipelineMode: options.pipelineMode,
    openai,
    cases: evaluatedCases,
    summary: {
      caseCount: evaluatedCases.length,
      autoMetricsTotal,
      autoMetricsPass,
      allAutoMetricsPass: autoMetricsPass === autoMetricsTotal,
      humanReviewRequired: true,
      agentCompletionNote:
        "人手評価の最終判定は Human scope。Agent は自動メトリクス + artifact 出力まで。",
    },
  };

  await mkdir(options.outputDir, { recursive: true });
  await writeFile(
    path.join(options.outputDir, "report.json"),
    `${JSON.stringify(report, null, 2)}\n`,
    "utf8",
  );
  await writeFile(
    path.join(options.outputDir, "cases.json"),
    `${JSON.stringify(evaluatedCases, null, 2)}\n`,
    "utf8",
  );
  await writeFile(
    path.join(options.outputDir, "summary.md"),
    buildSummaryMarkdown(report),
    "utf8",
  );

  console.log(
    `info: evaluation complete (${autoMetricsPass}/${autoMetricsTotal} auto metrics passed)`,
  );

  if (!report.summary.allAutoMetricsPass) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(`error: ${error.message}`);
  process.exit(1);
});
