import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { test } from "node:test";
import express from "express";

import {
  createMastersRouter,
  FEATURE_RULE_MASTERS_ERROR_CODES,
  FEATURE_RULE_MASTERS_METRICS,
  InMemoryFeatureRuleReader,
  type FeatureRuleMastersSuccessResponse,
} from "../../../../src/app/masters/index.js";
import { ApiError } from "../../../../src/middlewares/error/api-error.js";
import {
  ScaffoldApiLogger,
  type StructuredLogRecord,
} from "../../../../src/infrastructure/logger/logger.js";
import {
  registerErrorMiddleware,
  registerFoundationMiddlewares,
} from "../../../../src/middlewares/index.js";
import type { FeatureRuleReader } from "../../../../src/app/masters/types.js";

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
  ],
};

test("GET /api/v1/masters/feature-rules returns 2 groups without isActive/Pair", async () => {
  const logger = new ScaffoldApiLogger();
  const reader = new InMemoryFeatureRuleReader(sampleRules);

  await withMastersServer(
    { featureRuleReader: reader, logger },
    async (baseUrl) => {
      const response = await fetch(`${baseUrl}/api/v1/masters/feature-rules`, {
        headers: {
          Accept: "application/json",
          "X-Trace-Id": "trace-fr-001",
        },
      });
      assert.equal(response.status, 200);
      const body = (await response.json()) as FeatureRuleMastersSuccessResponse;
      assert.equal(body.meta.traceId, "trace-fr-001");
      assert.equal(body.data.configName, "mvp-semantic-config");
      assert.equal(body.data.versionLabel, "v1.0.0");
      assert.equal(body.data.baseValueRules.length, 2);
      assert.equal(body.data.conceptFeatureRules.length, 1);
      assert.equal(body.data.baseValueRules[0]?.ruleType, "relationship");
      assert.equal(body.data.baseValueRules[1]?.ruleType, "occasion");
      assert.equal(
        JSON.stringify(body).includes("isActive") ||
          JSON.stringify(body).includes("is_active"),
        false,
      );
      assert.equal(JSON.stringify(body).includes("pair"), false);
      assert.equal(
        JSON.stringify(body).includes("semanticConfigVersionId"),
        false,
      );
    },
  );

  assert.ok(
    logger.records.some(
      (r: StructuredLogRecord) =>
        r.eventName === FEATURE_RULE_MASTERS_METRICS.REQUEST_COUNT &&
        r.attributes?.httpStatus === 200,
    ),
  );
});

test("empty rule arrays return 200 when version resolved", async () => {
  const reader = new InMemoryFeatureRuleReader({
    configName: "mvp-semantic-config",
    versionLabel: "v1.0.0",
    baseValueRules: [],
    conceptFeatureRules: [],
  });

  await withMastersServer({ featureRuleReader: reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/masters/feature-rules`);
    assert.equal(response.status, 200);
    const body = (await response.json()) as FeatureRuleMastersSuccessResponse;
    assert.deepEqual(body.data.baseValueRules, []);
    assert.deepEqual(body.data.conceptFeatureRules, []);
  });
});

test("unknown query returns 400 GRS-REQ-001", async () => {
  const reader = new InMemoryFeatureRuleReader(sampleRules);

  await withMastersServer({ featureRuleReader: reader }, async (baseUrl) => {
    const response = await fetch(
      `${baseUrl}/api/v1/masters/feature-rules?foo=1`,
    );
    assert.equal(response.status, 400);
    const body = (await response.json()) as {
      error: { code: string };
    };
    assert.equal(body.error.code, FEATURE_RULE_MASTERS_ERROR_CODES.INVALID_REQUEST);
  });
});

test("mastersConfigResolved=false returns 500 GRS-CFG-005", async () => {
  const logger = new ScaffoldApiLogger();
  const reader = new InMemoryFeatureRuleReader(sampleRules);

  await withMastersServer(
    { featureRuleReader: reader, mastersConfigResolved: false, logger },
    async (baseUrl) => {
      const response = await fetch(`${baseUrl}/api/v1/masters/feature-rules`);
      assert.equal(response.status, 500);
      const body = (await response.json()) as {
        error: { code: string };
      };
      assert.equal(
        body.error.code,
        FEATURE_RULE_MASTERS_ERROR_CODES.CONFIG_UNRESOLVED,
      );
    },
  );

  assert.ok(
    logger.records.some(
      (r: StructuredLogRecord) =>
        r.eventName === FEATURE_RULE_MASTERS_METRICS.ERROR_COUNT &&
        r.attributes?.errorCode ===
          FEATURE_RULE_MASTERS_ERROR_CODES.CONFIG_UNRESOLVED,
    ),
  );
});

test("reader GRS-CFG-001 propagates as 500", async () => {
  const reader: FeatureRuleReader = {
    async getCurrentRules() {
      throw new ApiError({
        code: FEATURE_RULE_MASTERS_ERROR_CODES.CURRENT_NOT_FOUND,
        httpStatus: 500,
        message: "選択項目の取得に失敗しました。",
        retryable: true,
      });
    },
  };

  await withMastersServer({ featureRuleReader: reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/masters/feature-rules`);
    assert.equal(response.status, 500);
    const body = (await response.json()) as {
      error: { code: string };
    };
    assert.equal(
      body.error.code,
      FEATURE_RULE_MASTERS_ERROR_CODES.CURRENT_NOT_FOUND,
    );
  });
});
