import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { test } from "node:test";

import express from "express";

import {
  API_HEALTH_ERROR_CODES,
  API_HEALTH_STATUS_UNAVAILABLE,
  createHealthRouter,
} from "../../../../src/app/health/routes.js";
import { ScaffoldApiLogger } from "../../../../src/infrastructure/logger/logger.js";
import {
  registerErrorMiddleware,
  registerFoundationMiddlewares,
} from "../../../../src/middlewares/index.js";
import type { StructuredLogRecord } from "../../../../src/infrastructure/logger/types.js";
import { SCAFFOLD_ERROR_CODES } from "../../../../src/lib/error-response/constants.js";

type ErrorBody = {
  error: {
    code: string;
    message: string;
    retryable?: boolean;
  };
  meta: {
    traceId: string;
    requestId: string;
  };
  data?: unknown;
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

function createHealthApp(
  deps: Parameters<typeof createHealthRouter>[0],
): express.Express {
  const app = express();
  registerFoundationMiddlewares(app);
  app.use("/api/v1", createHealthRouter(deps));
  registerErrorMiddleware(app);
  return app;
}

test("unavailable resolveStatus returns 503 GRS-COM-003 ErrorResponse without data", async () => {
  const logger = new ScaffoldApiLogger();
  const app = createHealthApp({
    logger,
    resolveStatus: () => API_HEALTH_STATUS_UNAVAILABLE,
  });

  await withListeningApp(app, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/health`);
    assert.equal(response.status, 503);
    const body = (await response.json()) as ErrorBody;
    assert.equal(body.error.code, API_HEALTH_ERROR_CODES.UNAVAILABLE);
    assert.equal(body.error.retryable, true);
    assert.match(body.error.message, /サービスを利用できません/);
    assert.equal("data" in body, false);
    assert.ok(body.meta.traceId);
    assert.ok(body.meta.requestId);
    assert.equal(JSON.stringify(body).includes("stack"), false);
  });

  const errors = logger.records.filter(
    (r: StructuredLogRecord) => r.eventName === "api_error_count",
  );
  assert.equal(errors.length, 1);
  assert.equal(errors[0]?.attributes?.httpStatus, 503);
});

test("checkedAtFactory throw returns 500 GRS-COM-999 without stack in body", async () => {
  const logger = new ScaffoldApiLogger();
  const app = createHealthApp({
    logger,
    checkedAtFactory: () => {
      throw new Error("boom-for-unit-test");
    },
  });

  await withListeningApp(app, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/health`);
    assert.equal(response.status, 500);
    const body = (await response.json()) as ErrorBody;
    assert.equal(body.error.code, SCAFFOLD_ERROR_CODES.UNEXPECTED);
    assert.equal("data" in body, false);
    assert.equal(JSON.stringify(body).includes("boom-for-unit-test"), false);
    assert.equal(JSON.stringify(body).includes("stack"), false);
  });

  const errors = logger.records.filter(
    (r: StructuredLogRecord) => r.eventName === "api_error_count",
  );
  assert.equal(errors.length, 1);
  assert.equal(errors[0]?.attributes?.httpStatus, 500);
});
