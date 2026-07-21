import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { test } from "node:test";

import express from "express";

import {
  InMemoryRelationshipMasterReader,
  MASTERS_RELATIONSHIPS_ERROR_CODES,
  MASTERS_RELATIONSHIPS_METRICS,
  MASTERS_RELATIONSHIPS_PATH,
  UnresolvedRelationshipMasterReader,
  createMastersRouter,
} from "../../../../src/app/masters/index.js";
import { createApp } from "../../../../src/app.js";
import { ScaffoldApiLogger } from "../../../../src/infrastructure/logger/logger.js";
import {
  registerErrorMiddleware,
  registerFoundationMiddlewares,
} from "../../../../src/middlewares/index.js";
import { RelationshipMasterRepository } from "../../../../src/app/masters/relationship-repository.js";
import { ScaffoldDbSession } from "../../../../src/infrastructure/db/session.js";
import type { RelationshipsSuccessResponse } from "../../../../src/app/masters/types.js";

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

test("GET /api/v1/masters/relationships returns 200 with contract shape", async () => {
  const reader = new InMemoryRelationshipMasterReader([
    {
      relationshipCode: "colleague",
      relationshipLabel: "同僚",
      displayOrder: 20,
    },
    {
      relationshipCode: "boss",
      relationshipLabel: "上司",
      displayOrder: 10,
    },
  ]);
  const app = createMastersApp({
    relationshipReader: reader,
    generatedAtFactory: () => "2026-07-12T12:00:00.000Z",
  });

  await withListeningApp(app, async (baseUrl) => {
    const response = await fetch(`${baseUrl}${MASTERS_RELATIONSHIPS_PATH}`);
    assert.equal(response.status, 200);
    const body = (await response.json()) as RelationshipsSuccessResponse;
    assert.equal(body.meta.count, 2);
    assert.equal(body.data.relationships.length, 2);
    assert.equal(body.data.relationships[0]?.relationshipCode, "boss");
    assert.equal(body.data.relationships[0]?.relationshipLabel, "上司");
    assert.equal(body.data.relationships[0]?.displayOrder, 10);
    assert.equal(body.data.relationships[1]?.relationshipCode, "colleague");
    assert.ok(body.meta.traceId);
    assert.ok(body.meta.requestId);
    assert.equal(body.meta.generatedAt, "2026-07-12T12:00:00.000Z");
    assert.equal(
      Object.prototype.hasOwnProperty.call(
        body.data.relationships[0] ?? {},
        "isActive",
      ),
      false,
    );
  });
});

test("GET /api/v1/masters/relationships returns 200 empty array when no active rows", async () => {
  const app = createMastersApp({
    relationshipReader: new InMemoryRelationshipMasterReader([]),
  });

  await withListeningApp(app, async (baseUrl) => {
    const response = await fetch(`${baseUrl}${MASTERS_RELATIONSHIPS_PATH}`);
    assert.equal(response.status, 200);
    const body = (await response.json()) as RelationshipsSuccessResponse;
    assert.deepEqual(body.data.relationships, []);
    assert.equal(body.meta.count, 0);
  });
});

test("GET /api/v1/masters/relationships preserves X-Trace-Id", async () => {
  const app = createMastersApp({
    relationshipReader: new InMemoryRelationshipMasterReader([]),
  });
  const traceId = "550e8400-e29b-41d4-a716-446655440000";

  await withListeningApp(app, async (baseUrl) => {
    const response = await fetch(`${baseUrl}${MASTERS_RELATIONSHIPS_PATH}`, {
      headers: { "X-Trace-Id": traceId },
    });
    assert.equal(response.status, 200);
    const body = (await response.json()) as RelationshipsSuccessResponse;
    assert.equal(body.meta.traceId, traceId);
  });
});

test("GET /api/v1/masters/relationships returns GRS-CFG-005 when config unresolved", async () => {
  const app = createMastersApp({
    relationshipReader: new UnresolvedRelationshipMasterReader(),
  });

  await withListeningApp(app, async (baseUrl) => {
    const response = await fetch(`${baseUrl}${MASTERS_RELATIONSHIPS_PATH}`);
    assert.equal(response.status, 500);
    const body = (await response.json()) as {
      error?: { code?: string };
    };
    assert.equal(
      body.error?.code,
      MASTERS_RELATIONSHIPS_ERROR_CODES.MASTER_CONFIG_UNRESOLVED,
    );
  });
});

test("RelationshipMasterRepository maps DbError to GRS-DB-002", async () => {
  const session = new ScaffoldDbSession({ isAvailable: false });
  const repository = new RelationshipMasterRepository({ session });
  await assert.rejects(
    () => repository.listActive(),
    (error: unknown) => {
      assert.ok(error instanceof Error);
      assert.equal(
        (error as { code?: string }).code,
        MASTERS_RELATIONSHIPS_ERROR_CODES.DB_READ_FAILED,
      );
      return true;
    },
  );
});

test("RelationshipMasterRepository maps scaffold rows and filters via SQL", async () => {
  const session = new ScaffoldDbSession({
    queryRows: [
      {
        relationship_code: "boss",
        relationship_label: "上司",
        display_order: 10,
      },
    ],
  });
  const repository = new RelationshipMasterRepository({ session });
  const rows = await repository.listActive();
  assert.equal(rows.length, 1);
  assert.equal(rows[0]?.relationshipCode, "boss");
  assert.ok(session.operations[0]?.sql.includes("is_active = true"));
  assert.ok(session.operations[0]?.sql.includes("ORDER BY display_order"));
});

test("createMastersRouter records request and error metrics", async () => {
  const logger = new ScaffoldApiLogger();
  const app = createMastersApp({
    logger,
    relationshipReader: new UnresolvedRelationshipMasterReader(),
  });

  await withListeningApp(app, async (baseUrl) => {
    const response = await fetch(`${baseUrl}${MASTERS_RELATIONSHIPS_PATH}`);
    assert.equal(response.status, 500);
  });

  const requestEvents = logger.records.filter(
    (r) => r.eventName === MASTERS_RELATIONSHIPS_METRICS.REQUEST_COUNT,
  );
  const errorEvents = logger.records.filter(
    (r) => r.eventName === MASTERS_RELATIONSHIPS_METRICS.ERROR_COUNT,
  );
  assert.equal(requestEvents.length, 1);
  assert.equal(errorEvents.length, 1);
});

test("createApp mounts masters relationships (not 404)", async () => {
  await withListeningApp(createApp(), async (baseUrl) => {
    const response = await fetch(`${baseUrl}${MASTERS_RELATIONSHIPS_PATH}`);
    // DATABASE_URL 未設定時は GRS-CFG-005（500）。404 でないことのみ確認。
    assert.notEqual(response.status, 404);
  });
});

test("POST /api/v1/masters/relationships is rejected (not GET success)", async () => {
  const app = createMastersApp({
    relationshipReader: new InMemoryRelationshipMasterReader([]),
  });
  await withListeningApp(app, async (baseUrl) => {
    const response = await fetch(`${baseUrl}${MASTERS_RELATIONSHIPS_PATH}`, {
      method: "POST",
    });
    assert.notEqual(response.status, 200);
  });
});
