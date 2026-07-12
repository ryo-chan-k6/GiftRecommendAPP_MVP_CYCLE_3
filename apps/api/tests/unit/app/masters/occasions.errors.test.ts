import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { test } from "node:test";
import express from "express";

import {
  createMastersRouter,
  OCCASION_MASTERS_ERROR_CODES,
  OCCASION_MASTERS_METRICS,
  OccasionMasterRepository,
} from "../../../../src/app/masters/index.js";
import {
  DbError,
  ScaffoldDbSession,
  type DbHealth,
  type DbQueryParams,
  type DbQueryResult,
  type DbRow,
  type DbSession,
} from "../../../../src/infrastructure/db/index.js";
import {
  ScaffoldApiLogger,
  type StructuredLogRecord,
} from "../../../../src/infrastructure/logger/logger.js";
import {
  registerErrorMiddleware,
  registerFoundationMiddlewares,
} from "../../../../src/middlewares/index.js";

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

/** query 時に DbError を投げる session（DB_QUERY_FAILED 経路）。 */
class QueryFailSession implements DbSession {
  readonly backend = "scaffold-fail";

  healthCheck(): DbHealth {
    return { isAvailable: true, backend: this.backend };
  }

  async query<TRow extends DbRow = DbRow>(
    _sql: string,
    _params?: DbQueryParams,
  ): Promise<DbQueryResult<TRow>> {
    throw new DbError({
      code: "DB_QUERY_FAILED",
      message: "simulated query failure",
      retryable: true,
    });
  }

  async execute(): Promise<number> {
    return 0;
  }
}

test("DB_QUERY_FAILED maps to 500 GRS-DB-002 without stack or data", async () => {
  const logger = new ScaffoldApiLogger();

  await withMastersServer(
    { dbSession: new QueryFailSession(), logger },
    async (baseUrl) => {
      const response = await fetch(`${baseUrl}/api/v1/masters/occasions`);
      assert.equal(response.status, 500);
      const body = (await response.json()) as ErrorBody;
      assert.equal(body.error.code, OCCASION_MASTERS_ERROR_CODES.DB_READ_FAILED);
      assert.match(body.error.message, /データ取得に失敗/);
      assert.equal("data" in body, false);
      assert.equal(JSON.stringify(body).includes("stack"), false);
      assert.equal(JSON.stringify(body).includes("simulated query"), false);
      assert.ok(body.meta.traceId);
      assert.ok(body.meta.requestId);
    },
  );

  const requestMetrics = logger.records.filter(
    (r: StructuredLogRecord) =>
      r.eventName === OCCASION_MASTERS_METRICS.REQUEST_COUNT,
  );
  const errorMetrics = logger.records.filter(
    (r: StructuredLogRecord) =>
      r.eventName === OCCASION_MASTERS_METRICS.ERROR_COUNT,
  );
  assert.equal(requestMetrics.length, 1);
  assert.equal(errorMetrics.length, 1);
  assert.equal(
    errorMetrics[0]?.attributes?.errorCode,
    OCCASION_MASTERS_ERROR_CODES.DB_READ_FAILED,
  );
});

test("GRS-CFG-005 ErrorResponse has no stack and records error metric", async () => {
  const logger = new ScaffoldApiLogger();

  await withMastersServer(
    {
      dbSession: new ScaffoldDbSession({ queryRows: [] }),
      mastersConfigResolved: false,
      logger,
    },
    async (baseUrl) => {
      const response = await fetch(`${baseUrl}/api/v1/masters/occasions`, {
        headers: { "X-Trace-Id": "trace-cfg-005" },
      });
      assert.equal(response.status, 500);
      const body = (await response.json()) as ErrorBody;
      assert.equal(
        body.error.code,
        OCCASION_MASTERS_ERROR_CODES.CONFIG_UNRESOLVED,
      );
      assert.match(body.error.message, /選択項目の取得に失敗/);
      assert.equal(body.meta.traceId, "trace-cfg-005");
      assert.equal(JSON.stringify(body).includes("stack"), false);
    },
  );

  assert.ok(
    logger.records.some(
      (r: StructuredLogRecord) =>
        r.eventName === OCCASION_MASTERS_METRICS.ERROR_COUNT &&
        r.attributes?.errorCode ===
          OCCASION_MASTERS_ERROR_CODES.CONFIG_UNRESOLVED,
    ),
  );
});

test("non-GET method is not handled as success (404/405)", async () => {
  await withMastersServer(
    { dbSession: new ScaffoldDbSession({ queryRows: [] }) },
    async (baseUrl) => {
      const response = await fetch(`${baseUrl}/api/v1/masters/occasions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      assert.ok([404, 405].includes(response.status));
    },
  );
});

test("GET is idempotent for empty scaffold response", async () => {
  const session = new ScaffoldDbSession({ queryRows: [] });

  await withMastersServer({ dbSession: session }, async (baseUrl) => {
    const first = await fetch(`${baseUrl}/api/v1/masters/occasions`);
    const second = await fetch(`${baseUrl}/api/v1/masters/occasions`);
    assert.equal(first.status, 200);
    assert.equal(second.status, 200);
    const a = (await first.json()) as { meta: { count: number } };
    const b = (await second.json()) as { meta: { count: number } };
    assert.equal(a.meta.count, 0);
    assert.equal(b.meta.count, 0);
  });
});

test("OccasionMasterRepository maps rows and builds SELECT with filters", async () => {
  const session = new ScaffoldDbSession({
    queryRows: [
      {
        occasion_code: "thanks",
        occasion_label: "お礼",
        display_order: 1,
      },
    ],
  });
  const repository = new OccasionMasterRepository({ session });
  const items = await repository.listActive();
  assert.equal(items.length, 1);
  assert.deepEqual(items[0], {
    occasionCode: "thanks",
    occasionLabel: "お礼",
    displayOrder: 1,
  });
  assert.ok(
    session.operations[0]?.sql.includes("WHERE is_active = true"),
  );
  assert.ok(
    session.operations[0]?.sql.includes(
      "ORDER BY display_order ASC, occasion_code ASC",
    ),
  );
});

test("OccasionMasterRepository throws GRS-DB-002 when health unavailable", async () => {
  const repository = new OccasionMasterRepository({
    session: new ScaffoldDbSession({ isAvailable: false }),
  });
  await assert.rejects(
    () => repository.listActive(),
    (error: unknown) => {
      assert.ok(error instanceof Error);
      assert.equal(
        (error as { code?: string }).code,
        OCCASION_MASTERS_ERROR_CODES.DB_READ_FAILED,
      );
      return true;
    },
  );
});
