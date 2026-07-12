import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { test } from "node:test";

import express from "express";

import {
  API_HEALTH_API_VERSION,
  API_HEALTH_SERVICE,
  API_HEALTH_STATUS_OK,
  createHealthRouter,
} from "../../../../src/app/health/routes.js";
import { createApp } from "../../../../src/app.js";
import { ScaffoldApiLogger } from "../../../../src/infrastructure/logger/logger.js";
import {
  registerErrorMiddleware,
  registerFoundationMiddlewares,
} from "../../../../src/middlewares/index.js";
import type { StructuredLogRecord } from "../../../../src/infrastructure/logger/types.js";

type HealthSuccessBody = {
  data: {
    status: string;
    service: string;
    apiVersion: string;
    checkedAt?: string;
  };
  meta: {
    traceId: string;
    requestId: string;
    generatedAt?: string;
  };
};

async function withListeningApp(
  app: express.Express,
  run: (baseUrl: string) => Promise<void>,
): Promise<void> {
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

test("GET /api/v1/health returns 200 with contract shape (ok / okuri / v1)", async () => {
  await withListeningApp(createApp(), async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/health`);
    assert.equal(response.status, 200);
    const body = (await response.json()) as HealthSuccessBody;
    assert.equal(body.data.status, API_HEALTH_STATUS_OK);
    assert.equal(body.data.service, API_HEALTH_SERVICE);
    assert.equal(body.data.apiVersion, API_HEALTH_API_VERSION);
    assert.ok(body.data.checkedAt);
    assert.ok(body.meta.traceId);
    assert.ok(body.meta.requestId);
    assert.ok(body.meta.generatedAt);
  });
});

test("GET /api/v1/health preserves X-Trace-Id in meta.traceId", async () => {
  await withListeningApp(createApp(), async (baseUrl) => {
    const traceId = "550e8400-e29b-41d4-a716-446655440000";
    const response = await fetch(`${baseUrl}/api/v1/health`, {
      headers: { "X-Trace-Id": traceId },
    });
    assert.equal(response.status, 200);
    const body = (await response.json()) as HealthSuccessBody;
    assert.equal(body.meta.traceId, traceId);
  });
});

test("GET /api/v1/health is idempotent (no side-effectful state change)", async () => {
  await withListeningApp(createApp(), async (baseUrl) => {
    const first = await fetch(`${baseUrl}/api/v1/health`);
    const second = await fetch(`${baseUrl}/api/v1/health`);
    assert.equal(first.status, 200);
    assert.equal(second.status, 200);
    const body1 = (await first.json()) as HealthSuccessBody;
    const body2 = (await second.json()) as HealthSuccessBody;
    assert.equal(body1.data.status, API_HEALTH_STATUS_OK);
    assert.equal(body2.data.status, API_HEALTH_STATUS_OK);
    assert.equal(body1.data.service, body2.data.service);
  });
});

test("createHealthRouter records api_health_check via optional logger", async () => {
  const logger = new ScaffoldApiLogger();
  const app = express();
  registerFoundationMiddlewares(app);
  app.use("/api/v1", createHealthRouter({ logger }));
  registerErrorMiddleware(app);

  await withListeningApp(app, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/health`);
    assert.equal(response.status, 200);
  });

  const events = logger.records.filter(
    (r: StructuredLogRecord) => r.eventName === "api_health_check",
  );
  assert.equal(events.length, 1);
  assert.equal(events[0]?.attributes?.status, API_HEALTH_STATUS_OK);
  assert.equal(events[0]?.attributes?.httpStatus, 200);
  // Secret / 接続文字列相当のキーがログに無いこと
  const attrs = events[0]?.attributes ?? {};
  assert.equal("databaseUrl" in attrs, false);
  assert.equal("apiKey" in attrs, false);
});
