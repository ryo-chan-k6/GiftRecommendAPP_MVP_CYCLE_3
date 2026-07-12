import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { test } from "node:test";

import express from "express";

import {
  InMemoryRelationshipMasterReader,
  MASTERS_RELATIONSHIPS_ERROR_CODES,
  MASTERS_RELATIONSHIPS_METRICS,
  MASTERS_RELATIONSHIPS_PATH,
  createMastersRouter,
  isDatabaseUrlConfigured,
} from "../../../../src/app/masters/index.js";
import { ScaffoldApiLogger } from "../../../../src/infrastructure/logger/logger.js";
import {
  registerErrorMiddleware,
  registerFoundationMiddlewares,
} from "../../../../src/middlewares/index.js";
import type { RelationshipsSuccessResponse } from "../../../../src/app/masters/types.js";
import type { RelationshipMasterReader } from "../../../../src/app/masters/types.js";

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

function createMastersApp(
  deps: Parameters<typeof createMastersRouter>[0] = {},
): express.Express {
  const app = express();
  registerFoundationMiddlewares(app);
  app.use("/api/v1/masters", createMastersRouter(deps));
  registerErrorMiddleware(app);
  return app;
}

test("GET /relationships is idempotent across repeated calls", async () => {
  const reader = new InMemoryRelationshipMasterReader([
    {
      relationshipCode: "boss",
      relationshipLabel: "上司",
      displayOrder: 10,
    },
  ]);
  const app = createMastersApp({ relationshipReader: reader });

  await withListeningApp(app, async (baseUrl) => {
    const first = await fetch(`${baseUrl}${MASTERS_RELATIONSHIPS_PATH}`);
    const second = await fetch(`${baseUrl}${MASTERS_RELATIONSHIPS_PATH}`);
    assert.equal(first.status, 200);
    assert.equal(second.status, 200);
    const body1 = (await first.json()) as RelationshipsSuccessResponse;
    const body2 = (await second.json()) as RelationshipsSuccessResponse;
    assert.deepEqual(body1.data.relationships, body2.data.relationships);
    assert.equal(body1.meta.count, body2.meta.count);
  });
});

test("GET /relationships includes generated meta.requestId", async () => {
  const app = createMastersApp({
    relationshipReader: new InMemoryRelationshipMasterReader([]),
  });

  await withListeningApp(app, async (baseUrl) => {
    const response = await fetch(`${baseUrl}${MASTERS_RELATIONSHIPS_PATH}`, {
      headers: { "X-Request-Id": "client-supplied-should-not-leak-secret" },
    });
    assert.equal(response.status, 200);
    const body = (await response.json()) as RelationshipsSuccessResponse;
    // 現行 request-meta は X-Request-Id を採番で上書き（共通 middleware 方針）。
    assert.match(body.meta.requestId, /^req_/);
    assert.notEqual(body.meta.requestId, "client-supplied-should-not-leak-secret");
  });
});

test("createMastersRouter records request_count on success", async () => {
  const logger = new ScaffoldApiLogger();
  const app = createMastersApp({
    logger,
    relationshipReader: new InMemoryRelationshipMasterReader([
      {
        relationshipCode: "friend",
        relationshipLabel: "友人",
        displayOrder: 30,
      },
    ]),
  });

  await withListeningApp(app, async (baseUrl) => {
    const response = await fetch(`${baseUrl}${MASTERS_RELATIONSHIPS_PATH}`);
    assert.equal(response.status, 200);
  });

  const requestEvents = logger.records.filter(
    (r) => r.eventName === MASTERS_RELATIONSHIPS_METRICS.REQUEST_COUNT,
  );
  const errorEvents = logger.records.filter(
    (r) => r.eventName === MASTERS_RELATIONSHIPS_METRICS.ERROR_COUNT,
  );
  assert.equal(requestEvents.length, 1);
  assert.equal(errorEvents.length, 0);
  assert.equal(requestEvents[0]?.attributes?.httpStatus, 200);
  assert.equal(requestEvents[0]?.attributes?.count, 1);
});

test("unexpected reader failure maps to GRS-COM-999 without leaking internals", async () => {
  const reader: RelationshipMasterReader = {
    async listActive() {
      throw new Error(
        "connection failed postgresql://user:secret@localhost:5432/db SELECT * FROM relationship_master",
      );
    },
  };
  const app = createMastersApp({ relationshipReader: reader });

  await withListeningApp(app, async (baseUrl) => {
    const response = await fetch(`${baseUrl}${MASTERS_RELATIONSHIPS_PATH}`);
    assert.equal(response.status, 500);
    const body = (await response.json()) as {
      error?: { code?: string; message?: string };
    };
    assert.equal(body.error?.code, MASTERS_RELATIONSHIPS_ERROR_CODES.UNEXPECTED);
    const serialized = JSON.stringify(body);
    assert.equal(serialized.includes("postgresql://"), false);
    assert.equal(serialized.includes("secret"), false);
    assert.equal(serialized.includes("SELECT *"), false);
  });
});

test("displayOrder tie-break sorts by relationshipCode ascending", async () => {
  const app = createMastersApp({
    relationshipReader: new InMemoryRelationshipMasterReader([
      {
        relationshipCode: "zebra",
        relationshipLabel: "Z",
        displayOrder: 10,
      },
      {
        relationshipCode: "apple",
        relationshipLabel: "A",
        displayOrder: 10,
      },
    ]),
  });

  await withListeningApp(app, async (baseUrl) => {
    const response = await fetch(`${baseUrl}${MASTERS_RELATIONSHIPS_PATH}`);
    assert.equal(response.status, 200);
    const body = (await response.json()) as RelationshipsSuccessResponse;
    assert.equal(body.data.relationships[0]?.relationshipCode, "apple");
    assert.equal(body.data.relationships[1]?.relationshipCode, "zebra");
  });
});

test("isDatabaseUrlConfigured rejects missing and scaffold URLs", () => {
  assert.equal(isDatabaseUrlConfigured(undefined), false);
  assert.equal(isDatabaseUrlConfigured(""), false);
  assert.equal(isDatabaseUrlConfigured("   "), false);
  assert.equal(isDatabaseUrlConfigured("scaffold://local"), false);
  assert.equal(
    isDatabaseUrlConfigured("postgres://localhost/gift_recommend"),
    true,
  );
});
