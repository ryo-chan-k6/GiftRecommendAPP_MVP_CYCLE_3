import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { test } from "node:test";
import express from "express";

import {
  createMastersRouter,
  InMemorySemanticConfigReader,
  SEMANTIC_CONFIG_MASTERS_ERROR_CODES,
  SEMANTIC_CONFIG_MASTERS_METRICS,
  SEMANTIC_CONFIG_MASTERS_PATH,
  UnresolvedSemanticConfigReader,
  type SemanticConfigMastersSuccessResponse,
  type SemanticConfigReader,
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
    {
      featureCode: "emotion",
      featureLabel: "感情",
      featureGroup: "symbolic" as const,
      displayOrder: 2,
      isActive: true,
    },
  ],
};

type ErrorBody = {
  error: { code: string; message: string; retryable?: boolean };
  meta: { traceId: string; requestId: string };
  data?: unknown;
};

test("GET /semantic-configs is idempotent across repeated calls", async () => {
  const reader = new InMemorySemanticConfigReader(sampleSnapshot);

  await withMastersServer({ semanticConfigReader: reader }, async (baseUrl) => {
    const first = await fetch(`${baseUrl}${SEMANTIC_CONFIG_MASTERS_PATH}`);
    const second = await fetch(`${baseUrl}${SEMANTIC_CONFIG_MASTERS_PATH}`);
    assert.equal(first.status, 200);
    assert.equal(second.status, 200);
    const a = (await first.json()) as SemanticConfigMastersSuccessResponse;
    const b = (await second.json()) as SemanticConfigMastersSuccessResponse;
    assert.deepEqual(a.data, b.data);
  });
});

test("GET /semantic-configs preserves X-Trace-Id and generates requestId", async () => {
  const reader = new InMemorySemanticConfigReader(sampleSnapshot);

  await withMastersServer({ semanticConfigReader: reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}${SEMANTIC_CONFIG_MASTERS_PATH}`, {
      headers: {
        "X-Trace-Id": "trace-unit-007",
        "X-Request-Id": "client-supplied-should-not-leak",
      },
    });
    assert.equal(response.status, 200);
    const body = (await response.json()) as SemanticConfigMastersSuccessResponse;
    assert.equal(body.meta.traceId, "trace-unit-007");
    assert.match(body.meta.requestId, /^req_/);
    assert.notEqual(body.meta.requestId, "client-supplied-should-not-leak");
  });
});

test("success records request_count without error_count", async () => {
  const logger = new ScaffoldApiLogger();
  const reader = new InMemorySemanticConfigReader(sampleSnapshot);

  await withMastersServer(
    { semanticConfigReader: reader, logger },
    async (baseUrl) => {
      const response = await fetch(`${baseUrl}${SEMANTIC_CONFIG_MASTERS_PATH}`);
      assert.equal(response.status, 200);
    },
  );

  const requestEvents = logger.records.filter(
    (r: StructuredLogRecord) =>
      r.eventName === SEMANTIC_CONFIG_MASTERS_METRICS.REQUEST_COUNT,
  );
  const errorEvents = logger.records.filter(
    (r: StructuredLogRecord) =>
      r.eventName === SEMANTIC_CONFIG_MASTERS_METRICS.ERROR_COUNT,
  );
  assert.equal(requestEvents.length, 1);
  assert.equal(errorEvents.length, 0);
  assert.equal(requestEvents[0]?.attributes?.httpStatus, 200);
  assert.equal(requestEvents[0]?.attributes?.featureCount, 2);
});

test("GRS-CFG-002 via HTTP without stack or internal UUID leak", async () => {
  const logger = new ScaffoldApiLogger();
  const reader: SemanticConfigReader = {
    async getCurrentSnapshot() {
      throw new ApiError({
        code: SEMANTIC_CONFIG_MASTERS_ERROR_CODES.RESOLVE_FAILED,
        httpStatus: 500,
        message: "選択項目の取得に失敗しました。",
        retryable: true,
      });
    },
  };

  await withMastersServer(
    { semanticConfigReader: reader, logger },
    async (baseUrl) => {
      const response = await fetch(`${baseUrl}${SEMANTIC_CONFIG_MASTERS_PATH}`);
      assert.equal(response.status, 500);
      const body = (await response.json()) as ErrorBody;
      assert.equal(
        body.error.code,
        SEMANTIC_CONFIG_MASTERS_ERROR_CODES.RESOLVE_FAILED,
      );
      assert.equal("data" in body, false);
      const raw = JSON.stringify(body);
      assert.equal(raw.includes("stack"), false);
      assert.equal(raw.includes("semantic_config_version_id"), false);
    },
  );

  assert.ok(
    logger.records.some(
      (r: StructuredLogRecord) =>
        r.eventName === SEMANTIC_CONFIG_MASTERS_METRICS.ERROR_COUNT &&
        r.attributes?.errorCode ===
          SEMANTIC_CONFIG_MASTERS_ERROR_CODES.RESOLVE_FAILED,
    ),
  );
});

test("unexpected reader failure maps to GRS-COM-999 without leaking internals", async () => {
  const reader: SemanticConfigReader = {
    async getCurrentSnapshot() {
      throw new Error("secret-internal-db-url-should-not-leak");
    },
  };

  await withMastersServer({ semanticConfigReader: reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}${SEMANTIC_CONFIG_MASTERS_PATH}`);
    assert.equal(response.status, 500);
    const body = (await response.json()) as ErrorBody;
    assert.equal(
      body.error.code,
      SEMANTIC_CONFIG_MASTERS_ERROR_CODES.UNEXPECTED,
    );
    const raw = JSON.stringify(body);
    assert.equal(raw.includes("secret-internal-db-url-should-not-leak"), false);
    assert.equal(raw.includes("stack"), false);
  });
});

test("UnresolvedSemanticConfigReader returns GRS-CFG-001", async () => {
  await withMastersServer(
    { semanticConfigReader: new UnresolvedSemanticConfigReader() },
    async (baseUrl) => {
      const response = await fetch(`${baseUrl}${SEMANTIC_CONFIG_MASTERS_PATH}`);
      assert.equal(response.status, 500);
      const body = (await response.json()) as ErrorBody;
      assert.equal(
        body.error.code,
        SEMANTIC_CONFIG_MASTERS_ERROR_CODES.CURRENT_NOT_FOUND,
      );
      assert.match(body.error.message, /選択項目の取得に失敗/);
    },
  );
});

test("non-GET method is not handled as success (404/405)", async () => {
  await withMastersServer(
    { semanticConfigReader: new InMemorySemanticConfigReader(sampleSnapshot) },
    async (baseUrl) => {
      const response = await fetch(`${baseUrl}${SEMANTIC_CONFIG_MASTERS_PATH}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      assert.ok([404, 405].includes(response.status));
    },
  );
});

test("Response surfaces isActive and omits Rule fields", async () => {
  const reader = new InMemorySemanticConfigReader({
    ...sampleSnapshot,
    semanticConcepts: [
      {
        conceptCode: "thanks",
        conceptLabel: "感謝",
        conceptDescription: "お礼",
        isActive: true,
      },
    ],
  });

  await withMastersServer({ semanticConfigReader: reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}${SEMANTIC_CONFIG_MASTERS_PATH}`);
    assert.equal(response.status, 200);
    const body = (await response.json()) as SemanticConfigMastersSuccessResponse;
    assert.equal(body.data.semanticConcepts[0]?.isActive, true);
    assert.equal(body.data.featureDefinitions[0]?.isActive, true);
    const raw = JSON.stringify(body);
    assert.equal(raw.includes("semanticRule"), false);
    assert.equal(raw.includes("pairRule"), false);
    assert.equal(raw.includes("rule_json"), false);
  });
});
