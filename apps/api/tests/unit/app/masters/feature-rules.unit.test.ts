import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { test } from "node:test";
import express from "express";

import {
  createMastersRouter,
  FEATURE_RULE_MASTERS_ERROR_CODES,
  FEATURE_RULE_MASTERS_METRICS,
  FEATURE_RULE_MASTERS_PATH,
  InMemoryFeatureRuleReader,
  type FeatureRuleMastersSuccessResponse,
  type FeatureRuleReader,
} from "../../../../src/app/masters/index.js";
import {
  ScaffoldApiLogger,
  type StructuredLogRecord,
} from "../../../../src/infrastructure/logger/logger.js";
import {
  registerErrorMiddleware,
  registerFoundationMiddlewares,
} from "../../../../src/middlewares/index.js";

async function withMastersServer(
  deps: Parameters<typeof createMastersRouter>[0],
  run: (baseUrl: string) => Promise<void>,
): Promise<void> {
  const app = express();
  registerFoundationMiddlewares(app);
  app.use("/api/v1/masters", createMastersRouter(deps));
  registerErrorMiddleware(app);

  const server = app.listen(0);
  try {
    const address = server.address() as AddressInfo;
    await run(`http://127.0.0.1:${address.port}`);
  } finally {
    await new Promise<void>((resolve, reject) => {
      server.close((error: Error | undefined) =>
        error ? reject(error) : resolve(),
      );
    });
  }
}

const sampleRules = {
  configName: "mvp-semantic-config",
  versionLabel: "v1.0.0",
  baseValueRules: [
    {
      ruleType: "relationship" as const,
      relationshipCode: "friend",
      featureCode: "formality",
      featureBaseValue: 0.4,
    },
    {
      ruleType: "occasion" as const,
      occasionCode: "thanks",
      featureCode: "emotion",
      featureBaseValue: 0.7,
    },
  ],
  conceptFeatureRules: [
    {
      conceptCode: "formal_refined",
      featureCode: "formality",
      featureDelta: 0.15,
      polarity: "positive" as const,
    },
    {
      conceptCode: "warm_casual",
      featureCode: "intimacy",
      featureDelta: 0.1,
      // polarity optional — 省略ケース
    },
  ],
};

test("GET /feature-rules is idempotent across repeated calls", async () => {
  const reader = new InMemoryFeatureRuleReader(sampleRules);

  await withMastersServer({ featureRuleReader: reader }, async (baseUrl) => {
    const first = await fetch(`${baseUrl}${FEATURE_RULE_MASTERS_PATH}`);
    const second = await fetch(`${baseUrl}${FEATURE_RULE_MASTERS_PATH}`);
    assert.equal(first.status, 200);
    assert.equal(second.status, 200);
    const a = (await first.json()) as FeatureRuleMastersSuccessResponse;
    const b = (await second.json()) as FeatureRuleMastersSuccessResponse;
    assert.deepEqual(a.data, b.data);
  });
});

test("GET /feature-rules preserves X-Trace-Id and generates requestId", async () => {
  const reader = new InMemoryFeatureRuleReader(sampleRules);

  await withMastersServer({ featureRuleReader: reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}${FEATURE_RULE_MASTERS_PATH}`, {
      headers: {
        "X-Trace-Id": "trace-unit-008",
        "X-Request-Id": "client-supplied-should-not-leak",
      },
    });
    assert.equal(response.status, 200);
    const body = (await response.json()) as FeatureRuleMastersSuccessResponse;
    assert.equal(body.meta.traceId, "trace-unit-008");
    assert.match(body.meta.requestId, /^req_/);
    assert.notEqual(body.meta.requestId, "client-supplied-should-not-leak");
  });
});

test("conceptFeatureRules omits polarity when not set", async () => {
  const reader = new InMemoryFeatureRuleReader(sampleRules);

  await withMastersServer({ featureRuleReader: reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}${FEATURE_RULE_MASTERS_PATH}`);
    assert.equal(response.status, 200);
    const body = (await response.json()) as FeatureRuleMastersSuccessResponse;
    const withPolarity = body.data.conceptFeatureRules.find(
      (r) => r.conceptCode === "formal_refined",
    );
    const withoutPolarity = body.data.conceptFeatureRules.find(
      (r) => r.conceptCode === "warm_casual",
    );
    assert.equal(withPolarity?.polarity, "positive");
    assert.equal(withoutPolarity?.polarity, undefined);
    assert.equal(
      Object.prototype.hasOwnProperty.call(withoutPolarity ?? {}, "polarity"),
      false,
    );
  });
});

test("POST /feature-rules is not routed as success (non-GET)", async () => {
  const reader = new InMemoryFeatureRuleReader(sampleRules);

  await withMastersServer({ featureRuleReader: reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}${FEATURE_RULE_MASTERS_PATH}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    assert.notEqual(response.status, 200);
  });
});

test("error path records both request_count and error_count", async () => {
  const logger = new ScaffoldApiLogger();
  const reader: FeatureRuleReader = {
    async getCurrentRules() {
      throw new Error("boom");
    },
  };

  await withMastersServer(
    { featureRuleReader: reader, logger },
    async (baseUrl) => {
      const response = await fetch(`${baseUrl}${FEATURE_RULE_MASTERS_PATH}`);
      assert.equal(response.status, 500);
      const body = (await response.json()) as { error: { code: string } };
      assert.equal(body.error.code, FEATURE_RULE_MASTERS_ERROR_CODES.UNEXPECTED);
    },
  );

  assert.ok(
    logger.records.some(
      (r: StructuredLogRecord) =>
        r.eventName === FEATURE_RULE_MASTERS_METRICS.REQUEST_COUNT &&
        r.attributes?.httpStatus === 500,
    ),
  );
  assert.ok(
    logger.records.some(
      (r: StructuredLogRecord) =>
        r.eventName === FEATURE_RULE_MASTERS_METRICS.ERROR_COUNT &&
        r.attributes?.errorCode === FEATURE_RULE_MASTERS_ERROR_CODES.UNEXPECTED,
    ),
  );
});
