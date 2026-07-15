import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { test } from "node:test";
import express from "express";

import {
  createItemsRouter,
  InMemoryItemDetailRepository,
  ITEM_DETAIL_ERROR_CODES,
  ITEM_DETAIL_ERROR_MESSAGES,
  ITEM_DETAIL_METRICS,
  ITEM_ID_MAX_LENGTH,
  ItemDetailRepository,
  POPULARITY_BADGE_LABEL,
  type ItemDetailRecord,
  type ItemDetailSuccessResponse,
} from "../../../../src/app/items/index.js";
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
import { ApiError } from "../../../../src/middlewares/error/api-error.js";
import {
  registerErrorMiddleware,
  registerFoundationMiddlewares,
} from "../../../../src/middlewares/index.js";

const ACTIVE_ITEM_ID = "550e8400-e29b-41d4-a716-446655440001";
const INACTIVE_ITEM_ID = "550e8400-e29b-41d4-a716-446655440002";
const NO_IMAGE_ITEM_ID = "550e8400-e29b-41d4-a716-446655440003";
const NO_BADGE_ITEM_ID = "550e8400-e29b-41d4-a716-446655440004";
const UNKNOWN_ITEM_ID = "550e8400-e29b-41d4-a716-446655440099";

const FORBIDDEN_RESPONSE_FRAGMENTS = [
  "feature",
  "embedding",
  "normalized_hash",
  "context_score",
  "contextScore",
  "lambda_ctx",
  "lambdaCtx",
  "internal_score",
  "popularity_signal",
  "stack",
] as const;

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

function createSeedRepository() {
  return new InMemoryItemDetailRepository({
    items: [
      {
        itemId: ACTIVE_ITEM_ID,
        itemName: "上品な焼き菓子ギフトセット",
        price: 4320,
        itemUrl: "https://example.com/item/001",
        catchcopy: "贈り物にぴったり",
        itemCaption: "厳選素材の焼き菓子詰合せです。",
        externalGenreId: "100227",
        genreName: "スイーツ",
        isActive: true,
        images: [
          {
            imageUrl: "https://example.com/images/primary.jpg",
            imageSizeType: "medium",
            displayOrder: 0,
            isPrimary: true,
          },
        ],
        reviewAverage: 4.2,
        reviewCount: 128,
        popularityRank: 12,
      },
      {
        itemId: INACTIVE_ITEM_ID,
        itemName: "非公開商品",
        price: 1000,
        itemUrl: "https://example.com/item/inactive",
        catchcopy: null,
        itemCaption: null,
        externalGenreId: null,
        genreName: null,
        isActive: false,
        images: [],
        reviewAverage: null,
        reviewCount: null,
        popularityRank: null,
      },
      {
        itemId: NO_IMAGE_ITEM_ID,
        itemName: "画像なし商品",
        price: 2000,
        itemUrl: "https://example.com/item/no-image",
        catchcopy: null,
        itemCaption: null,
        externalGenreId: null,
        genreName: null,
        isActive: true,
        images: [],
        reviewAverage: null,
        reviewCount: null,
        popularityRank: null,
      },
      {
        itemId: NO_BADGE_ITEM_ID,
        itemName: "バッジなし商品",
        price: 3000,
        itemUrl: "https://example.com/item/no-badge",
        catchcopy: null,
        itemCaption: null,
        externalGenreId: "100227",
        genreName: "スイーツ",
        isActive: true,
        images: [
          {
            imageUrl: "https://example.com/images/badgeless.jpg",
            imageSizeType: "medium",
            displayOrder: 0,
            isPrimary: true,
          },
        ],
        reviewAverage: null,
        reviewCount: null,
        popularityRank: null,
      },
    ],
  });
}

async function withItemsServer(
  deps: Parameters<typeof createItemsRouter>[0],
  run: (baseUrl: string) => Promise<void>,
): Promise<void> {
  const app = express();
  registerFoundationMiddlewares(app);
  app.use("/api/v1/items", createItemsRouter(deps));
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

function assertNoForbiddenFragments(serialized: string): void {
  for (const fragment of FORBIDDEN_RESPONSE_FRAGMENTS) {
    assert.equal(
      serialized.includes(fragment),
      false,
      `response must not include "${fragment}"`,
    );
  }
  assert.equal(serialized.includes("GRS-ITM-003"), false);
}

function requestMetricRecords(
  logger: ScaffoldApiLogger,
): StructuredLogRecord[] {
  return logger.records.filter(
    (record: StructuredLogRecord) =>
      record.eventName === ITEM_DETAIL_METRICS.REQUEST_COUNT,
  );
}

function notFoundMetricRecords(
  logger: ScaffoldApiLogger,
): StructuredLogRecord[] {
  return logger.records.filter(
    (record: StructuredLogRecord) =>
      record.eventName === ITEM_DETAIL_METRICS.NOT_FOUND_COUNT,
  );
}

class ReadFailRepository extends InMemoryItemDetailRepository {
  override async findDetail(_itemId: string): Promise<ItemDetailRecord | null> {
    throw new ApiError({
      code: ITEM_DETAIL_ERROR_CODES.DB_QUERY_FAILED,
      httpStatus: 500,
      message: ITEM_DETAIL_ERROR_MESSAGES.DB_QUERY_FAILED,
      retryable: true,
    });
  }
}

class DbUnavailableRepository extends InMemoryItemDetailRepository {
  override async findDetail(_itemId: string): Promise<ItemDetailRecord | null> {
    throw new ApiError({
      code: ITEM_DETAIL_ERROR_CODES.DB_UNAVAILABLE,
      httpStatus: 503,
      message: ITEM_DETAIL_ERROR_MESSAGES.DB_UNAVAILABLE,
      retryable: true,
    });
  }
}

class UnexpectedFailRepository extends InMemoryItemDetailRepository {
  override async findDetail(_itemId: string): Promise<ItemDetailRecord | null> {
    throw new Error("simulated unexpected repository failure");
  }
}

/** query 時に DbError を投げる session（ItemDetailRepository 経由の DB 失敗）。 */
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

test("GET item detail 404 records request_count and item_not_found_count", async () => {
  const logger = new ScaffoldApiLogger();
  const reader = createSeedRepository();

  await withItemsServer({ reader, logger }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/items/${UNKNOWN_ITEM_ID}`, {
      headers: {
        Accept: "application/json",
        "X-Trace-Id": "trace-not-found",
      },
    });

    assert.equal(response.status, 404);
    const body = (await response.json()) as ErrorBody;
    assert.equal(body.error.code, ITEM_DETAIL_ERROR_CODES.NOT_FOUND);
    assert.equal(body.meta.traceId, "trace-not-found");
    assert.match(body.meta.requestId, /^req_/);
    assertNoForbiddenFragments(JSON.stringify(body));
  });

  assert.equal(requestMetricRecords(logger).length, 1);
  assert.equal(
    requestMetricRecords(logger)[0]?.attributes?.httpStatus,
    404,
  );
  assert.equal(
    requestMetricRecords(logger)[0]?.attributes?.code,
    ITEM_DETAIL_ERROR_CODES.NOT_FOUND,
  );
  assert.equal(notFoundMetricRecords(logger).length, 1);
  assert.equal(
    notFoundMetricRecords(logger)[0]?.attributes?.code,
    ITEM_DETAIL_ERROR_CODES.NOT_FOUND,
  );
});

test("GET inactive item 422 does not increment item_not_found_count", async () => {
  const logger = new ScaffoldApiLogger();
  const reader = createSeedRepository();

  await withItemsServer({ reader, logger }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/items/${INACTIVE_ITEM_ID}`);
    assert.equal(response.status, 422);
    const body = (await response.json()) as ErrorBody;
    assert.equal(body.error.code, ITEM_DETAIL_ERROR_CODES.INACTIVE);
    assert.notEqual(body.error.code, ITEM_DETAIL_ERROR_CODES.NOT_FOUND);
  });

  assert.equal(requestMetricRecords(logger).length, 1);
  assert.equal(notFoundMetricRecords(logger).length, 0);
});

test("GET item without images returns 200 and never GRS-ITM-003", async () => {
  const reader = createSeedRepository();

  await withItemsServer({ reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/items/${NO_IMAGE_ITEM_ID}`);
    assert.equal(response.status, 200);
    const body = (await response.json()) as ItemDetailSuccessResponse;
    assert.equal("itemImageUrl" in body.data, false);
    assert.equal("images" in body.data, false);
    assert.equal("popularityBadge" in body.data, false);
    assertNoForbiddenFragments(JSON.stringify(body));
  });
});

test("GET item without popularity rank omits popularityBadge", async () => {
  const reader = createSeedRepository();

  await withItemsServer({ reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/items/${NO_BADGE_ITEM_ID}`);
    assert.equal(response.status, 200);
    const body = (await response.json()) as ItemDetailSuccessResponse;
    assert.equal("popularityBadge" in body.data, false);
    assert.equal(body.data.itemImageUrl, "https://example.com/images/badgeless.jpg");
  });
});

test("GET item with popularity rank includes popularityBadge", async () => {
  const reader = createSeedRepository();

  await withItemsServer({ reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/items/${ACTIVE_ITEM_ID}`);
    assert.equal(response.status, 200);
    const body = (await response.json()) as ItemDetailSuccessResponse;
    assert.equal(body.data.popularityBadge?.label, POPULARITY_BADGE_LABEL);
    assert.equal(body.data.popularityBadge?.rank, 12);
  });
});

test("GET item detail returns 400 GRS-REQ-001 for whitespace-only itemId", async () => {
  const logger = new ScaffoldApiLogger();
  const reader = createSeedRepository();

  await withItemsServer({ reader, logger }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/items/%20%20`);
    assert.equal(response.status, 400);
    const body = (await response.json()) as ErrorBody;
    assert.equal(body.error.code, ITEM_DETAIL_ERROR_CODES.INVALID_REQUEST);
  });

  assert.equal(requestMetricRecords(logger).length, 1);
  assert.equal(
    requestMetricRecords(logger)[0]?.attributes?.code,
    ITEM_DETAIL_ERROR_CODES.INVALID_REQUEST,
  );
  assert.equal(notFoundMetricRecords(logger).length, 0);
});

test("GET item detail returns 400 GRS-REQ-001 for maxLength overflow itemId", async () => {
  const reader = createSeedRepository();
  const tooLong = "a".repeat(ITEM_ID_MAX_LENGTH + 1);

  await withItemsServer({ reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/items/${tooLong}`);
    assert.equal(response.status, 400);
    const body = (await response.json()) as ErrorBody;
    assert.equal(body.error.code, ITEM_DETAIL_ERROR_CODES.INVALID_REQUEST);
  });
});

test("GET item detail returns 400 GRS-REQ-001 for unknown query with metrics", async () => {
  const logger = new ScaffoldApiLogger();
  const reader = createSeedRepository();

  await withItemsServer({ reader, logger }, async (baseUrl) => {
    const response = await fetch(
      `${baseUrl}/api/v1/items/${ACTIVE_ITEM_ID}?foo=bar`,
    );
    assert.equal(response.status, 400);
    const body = (await response.json()) as ErrorBody;
    assert.equal(body.error.code, ITEM_DETAIL_ERROR_CODES.INVALID_REQUEST);
    assertNoForbiddenFragments(JSON.stringify(body));
  });

  assert.equal(requestMetricRecords(logger).length, 1);
  assert.equal(
    requestMetricRecords(logger)[0]?.attributes?.code,
    ITEM_DETAIL_ERROR_CODES.INVALID_REQUEST,
  );
});

test("success and error responses omit internal fields and stack", async () => {
  const reader = createSeedRepository();

  await withItemsServer({ reader }, async (baseUrl) => {
    const success = await fetch(`${baseUrl}/api/v1/items/${ACTIVE_ITEM_ID}`);
    assert.equal(success.status, 200);
    assertNoForbiddenFragments(JSON.stringify(await success.json()));

    const error = await fetch(`${baseUrl}/api/v1/items/${UNKNOWN_ITEM_ID}`);
    assert.equal(error.status, 404);
    assertNoForbiddenFragments(JSON.stringify(await error.json()));
  });
});

test("X-Trace-Id propagates to meta.traceId on error responses", async () => {
  const reader = createSeedRepository();

  await withItemsServer({ reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/items/${INACTIVE_ITEM_ID}`, {
      headers: { "X-Trace-Id": "trace-error-422" },
    });
    assert.equal(response.status, 422);
    const body = (await response.json()) as ErrorBody;
    assert.equal(body.meta.traceId, "trace-error-422");
  });
});

test("meta.requestId is server-generated and does not echo client X-Request-Id", async () => {
  const reader = createSeedRepository();

  await withItemsServer({ reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/items/${ACTIVE_ITEM_ID}`, {
      headers: { "X-Request-Id": "client-supplied-should-not-leak" },
    });
    assert.equal(response.status, 200);
    const body = (await response.json()) as ItemDetailSuccessResponse;
    assert.match(body.meta.requestId, /^req_/);
    assert.notEqual(body.meta.requestId, "client-supplied-should-not-leak");
  });
});

test("ReadFailRepository returns 500 GRS-DB-002 without stack", async () => {
  const logger = new ScaffoldApiLogger();
  const reader = new ReadFailRepository();

  await withItemsServer({ reader, logger }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/items/${ACTIVE_ITEM_ID}`);
    assert.equal(response.status, 500);
    const body = (await response.json()) as ErrorBody;
    assert.equal(body.error.code, ITEM_DETAIL_ERROR_CODES.DB_QUERY_FAILED);
    assert.equal("data" in body, false);
    assertNoForbiddenFragments(JSON.stringify(body));
  });

  assert.equal(requestMetricRecords(logger).length, 1);
  assert.equal(
    requestMetricRecords(logger)[0]?.attributes?.code,
    ITEM_DETAIL_ERROR_CODES.DB_QUERY_FAILED,
  );
});

test("DbUnavailableRepository returns 503 GRS-DB-001", async () => {
  const logger = new ScaffoldApiLogger();
  const reader = new DbUnavailableRepository();

  await withItemsServer({ reader, logger }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/items/${ACTIVE_ITEM_ID}`);
    assert.equal(response.status, 503);
    const body = (await response.json()) as ErrorBody;
    assert.equal(body.error.code, ITEM_DETAIL_ERROR_CODES.DB_UNAVAILABLE);
    assert.equal(body.error.retryable, true);
  });

  assert.equal(requestMetricRecords(logger).length, 1);
  assert.equal(
    requestMetricRecords(logger)[0]?.attributes?.code,
    ITEM_DETAIL_ERROR_CODES.DB_UNAVAILABLE,
  );
});

test("UnexpectedFailRepository returns 500 GRS-ITM-999", async () => {
  const logger = new ScaffoldApiLogger();
  const reader = new UnexpectedFailRepository();

  await withItemsServer({ reader, logger }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/items/${ACTIVE_ITEM_ID}`);
    assert.equal(response.status, 500);
    const body = (await response.json()) as ErrorBody;
    assert.equal(body.error.code, ITEM_DETAIL_ERROR_CODES.UNEXPECTED);
    assert.equal(body.error.retryable, false);
    assertNoForbiddenFragments(JSON.stringify(body));
  });

  assert.equal(requestMetricRecords(logger).length, 1);
  assert.equal(
    requestMetricRecords(logger)[0]?.attributes?.code,
    ITEM_DETAIL_ERROR_CODES.UNEXPECTED,
  );
});

test("ItemDetailRepository maps DB_QUERY_FAILED to 500 GRS-DB-002", async () => {
  const logger = new ScaffoldApiLogger();

  await withItemsServer(
    {
      reader: new ItemDetailRepository({ session: new QueryFailSession() }),
      logger,
    },
    async (baseUrl) => {
      const response = await fetch(`${baseUrl}/api/v1/items/${ACTIVE_ITEM_ID}`);
      assert.equal(response.status, 500);
      const body = (await response.json()) as ErrorBody;
      assert.equal(body.error.code, ITEM_DETAIL_ERROR_CODES.DB_QUERY_FAILED);
      assert.equal(JSON.stringify(body).includes("simulated query"), false);
    },
  );

  assert.equal(requestMetricRecords(logger).length, 1);
});

test("ItemDetailRepository maps DB_UNAVAILABLE to 503 GRS-DB-001", async () => {
  const logger = new ScaffoldApiLogger();
  const session = new ScaffoldDbSession({ isAvailable: false });

  await withItemsServer(
    {
      reader: new ItemDetailRepository({ session }),
      logger,
    },
    async (baseUrl) => {
      const response = await fetch(`${baseUrl}/api/v1/items/${ACTIVE_ITEM_ID}`);
      assert.equal(response.status, 503);
      const body = (await response.json()) as ErrorBody;
      assert.equal(body.error.code, ITEM_DETAIL_ERROR_CODES.DB_UNAVAILABLE);
    },
  );

  assert.equal(requestMetricRecords(logger).length, 1);
});

test("non-GET method is not handled as success (404 or 405)", async () => {
  const reader = createSeedRepository();

  await withItemsServer({ reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/items/${ACTIVE_ITEM_ID}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    assert.ok([404, 405].includes(response.status));
  });
});

test(
  "§9.12 generated getItemDetail client typecheck",
  { skip: "consumer Task — Orval/generated typecheck is out of API unit-test scope" },
  () => {},
);

test(
  "§9.13 SCR-006 provider/consumer manual verification",
  { skip: "manual screen Task — SCR-006 UI integration is not automatable here" },
  () => {},
);
