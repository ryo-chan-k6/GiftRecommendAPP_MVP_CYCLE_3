import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { test } from "node:test";
import express from "express";

import {
  createMastersRouter,
  InMemorySemanticConfigReader,
  SEMANTIC_CONFIG_MASTERS_ERROR_CODES,
  SEMANTIC_CONFIG_MASTERS_METRICS,
  type SemanticConfigMastersSuccessResponse,
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
import type { SemanticConfigReader } from "../../../../src/app/masters/types.js";

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

const sampleSnapshot = {
  configName: "mvp-default",
  versionLabel: "v1",
  semanticConcepts: [
    {
      conceptCode: "thanks",
      conceptLabel: "感謝",
      conceptDescription: "お礼の気持ち",
      isActive: true,
    },
  ],
  featureDefinitions: [
    {
      featureCode: "formality",
      featureLabel: "フォーマル度",
      featureGroup: "social" as const,
      displayOrder: 1,
      isActive: true,
    },
  ],
};

test("GET /api/v1/masters/semantic-configs returns snapshot without UUID", async () => {
  const logger = new ScaffoldApiLogger();
  const reader = new InMemorySemanticConfigReader(sampleSnapshot);

  await withMastersServer(
    { semanticConfigReader: reader, logger },
    async (baseUrl) => {
      const response = await fetch(
        `${baseUrl}/api/v1/masters/semantic-configs`,
        {
          headers: {
            Accept: "application/json",
            "X-Trace-Id": "trace-sem-001",
          },
        },
      );
      assert.equal(response.status, 200);
      const body = (await response.json()) as SemanticConfigMastersSuccessResponse;
      assert.equal(body.meta.traceId, "trace-sem-001");
      assert.equal(body.data.configName, "mvp-default");
      assert.equal(body.data.versionLabel, "v1");
      assert.equal(body.data.semanticConcepts.length, 1);
      assert.equal(body.data.featureDefinitions.length, 1);
      assert.equal(body.data.semanticConcepts[0]?.isActive, true);
      assert.equal(
        JSON.stringify(body).includes("semantic_config_version_id"),
        false,
      );
      assert.equal(JSON.stringify(body).includes("semanticConfigVersionId"), false);
    },
  );

  assert.ok(
    logger.records.some(
      (r: StructuredLogRecord) =>
        r.eventName === SEMANTIC_CONFIG_MASTERS_METRICS.REQUEST_COUNT &&
        r.attributes?.httpStatus === 200,
    ),
  );
});

test("Concept empty array returns 200 when features exist", async () => {
  const reader = new InMemorySemanticConfigReader({
    ...sampleSnapshot,
    semanticConcepts: [],
  });

  await withMastersServer({ semanticConfigReader: reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/masters/semantic-configs`);
    assert.equal(response.status, 200);
    const body = (await response.json()) as SemanticConfigMastersSuccessResponse;
    assert.equal(body.data.semanticConcepts.length, 0);
    assert.equal(body.data.featureDefinitions.length, 1);
  });
});

test("unknown query returns 400 GRS-REQ-001", async () => {
  const logger = new ScaffoldApiLogger();
  const reader = new InMemorySemanticConfigReader(sampleSnapshot);

  await withMastersServer(
    { semanticConfigReader: reader, logger },
    async (baseUrl) => {
      const response = await fetch(
        `${baseUrl}/api/v1/masters/semantic-configs?foo=bar`,
      );
      assert.equal(response.status, 400);
      const body = (await response.json()) as {
        error: { code: string; message: string };
      };
      assert.equal(
        body.error.code,
        SEMANTIC_CONFIG_MASTERS_ERROR_CODES.INVALID_REQUEST,
      );
      assert.match(body.error.message, /条件を確認/);
    },
  );

  assert.ok(
    logger.records.some(
      (r: StructuredLogRecord) =>
        r.eventName === SEMANTIC_CONFIG_MASTERS_METRICS.ERROR_COUNT &&
        r.attributes?.errorCode ===
          SEMANTIC_CONFIG_MASTERS_ERROR_CODES.INVALID_REQUEST,
    ),
  );
});

test("GRS-CFG-001 when current not found", async () => {
  const reader: SemanticConfigReader = {
    async getCurrentSnapshot() {
      throw new ApiError({
        code: SEMANTIC_CONFIG_MASTERS_ERROR_CODES.CURRENT_NOT_FOUND,
        httpStatus: 500,
        message: "選択項目の取得に失敗しました。",
        retryable: true,
      });
    },
  };

  await withMastersServer({ semanticConfigReader: reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/masters/semantic-configs`);
    assert.equal(response.status, 500);
    const body = (await response.json()) as { error: { code: string } };
    assert.equal(
      body.error.code,
      SEMANTIC_CONFIG_MASTERS_ERROR_CODES.CURRENT_NOT_FOUND,
    );
  });
});

test("GRS-CFG-006 when feature definitions missing", async () => {
  const reader: SemanticConfigReader = {
    async getCurrentSnapshot() {
      throw new ApiError({
        code: SEMANTIC_CONFIG_MASTERS_ERROR_CODES.FEATURE_MISSING,
        httpStatus: 500,
        message: "選択項目の取得に失敗しました。",
        retryable: true,
      });
    },
  };

  await withMastersServer({ semanticConfigReader: reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/masters/semantic-configs`);
    assert.equal(response.status, 500);
    const body = (await response.json()) as { error: { code: string } };
    assert.equal(
      body.error.code,
      SEMANTIC_CONFIG_MASTERS_ERROR_CODES.FEATURE_MISSING,
    );
  });
});
