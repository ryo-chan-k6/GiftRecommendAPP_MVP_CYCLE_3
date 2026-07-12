import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { test } from "node:test";
import express from "express";

import {
  createMastersRouter,
  OCCASION_MASTERS_ERROR_CODES,
  OCCASION_MASTERS_METRICS,
  type OccasionMastersSuccessResponse,
} from "../../../../src/app/masters/index.js";
import { ScaffoldDbSession } from "../../../../src/infrastructure/db/index.js";
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

test("GET /api/v1/masters/occasions returns active rows without isActive/pair", async () => {
  const session = new ScaffoldDbSession({
    // Scaffold は SQL ORDER を適用しないため、契約順（display_order ASC）で渡す
    queryRows: [
      {
        occasion_code: "thanks",
        occasion_label: "お礼",
        display_order: 10,
        is_active: true,
      },
      {
        occasion_code: "birthday",
        occasion_label: "誕生日",
        display_order: 20,
        is_active: true,
      },
    ],
  });

  await withMastersServer({ dbSession: session }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/masters/occasions`, {
      headers: {
        Accept: "application/json",
        "X-Trace-Id": "trace-occ-001",
      },
    });
    assert.equal(response.status, 200);
    const body = (await response.json()) as OccasionMastersSuccessResponse;
    assert.equal(body.meta.traceId, "trace-occ-001");
    assert.equal(body.meta.count, 2);
    assert.equal(body.data.occasions.length, 2);
    assert.equal(body.data.occasions[0]?.occasionCode, "thanks");
    assert.equal(body.data.occasions[0]?.occasionLabel, "お礼");
    assert.equal(body.data.occasions[0]?.displayOrder, 10);
    assert.equal(
      "isActive" in (body.data.occasions[0] ?? {}),
      false,
    );
    assert.equal("pair" in body.data, false);
    assert.ok(
      session.operations.some(
        (op) =>
          op.kind === "query" &&
          op.sql.includes("is_active = true") &&
          op.sql.includes("ORDER BY display_order"),
      ),
    );
  });
});

test("GET /api/v1/masters/occasions returns 200 empty array when no rows", async () => {
  const session = new ScaffoldDbSession({ queryRows: [] });

  await withMastersServer({ dbSession: session }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/masters/occasions`);
    assert.equal(response.status, 200);
    const body = (await response.json()) as OccasionMastersSuccessResponse;
    assert.deepEqual(body.data.occasions, []);
    assert.equal(body.meta.count, 0);
  });
});

test("GET /api/v1/masters/occasions returns GRS-DB-002 when DB unavailable", async () => {
  const session = new ScaffoldDbSession({ isAvailable: false });

  await withMastersServer({ dbSession: session }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/masters/occasions`);
    assert.equal(response.status, 500);
    const body = (await response.json()) as {
      error?: { code?: string };
    };
    assert.equal(body.error?.code, OCCASION_MASTERS_ERROR_CODES.DB_READ_FAILED);
  });
});

test("GET /api/v1/masters/occasions returns GRS-CFG-005 when config unresolved", async () => {
  await withMastersServer(
    {
      dbSession: new ScaffoldDbSession({ queryRows: [] }),
      mastersConfigResolved: false,
    },
    async (baseUrl) => {
      const response = await fetch(`${baseUrl}/api/v1/masters/occasions`);
      assert.equal(response.status, 500);
      const body = (await response.json()) as {
        error?: { code?: string };
      };
      assert.equal(
        body.error?.code,
        OCCASION_MASTERS_ERROR_CODES.CONFIG_UNRESOLVED,
      );
    },
  );
});

test("createMastersRouter records masters_occasions metrics via logger", async () => {
  const logger = new ScaffoldApiLogger();
  const session = new ScaffoldDbSession({
    queryRows: [
      {
        occasion_code: "thanks",
        occasion_label: "お礼",
        display_order: 0,
      },
    ],
  });

  await withMastersServer(
    { dbSession: session, logger },
    async (baseUrl) => {
      const response = await fetch(`${baseUrl}/api/v1/masters/occasions`);
      assert.equal(response.status, 200);
    },
  );

  const requestMetric = logger.records.find(
    (r: StructuredLogRecord) =>
      r.eventName === OCCASION_MASTERS_METRICS.REQUEST_COUNT,
  );
  assert.ok(requestMetric);
  assert.equal(requestMetric?.attributes?.httpStatus, 200);
});
