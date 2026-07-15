import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { test } from "node:test";
import express from "express";

import {
  createItemsRouter,
  InMemoryItemDetailRepository,
  ITEM_DETAIL_ERROR_CODES,
  ITEM_DETAIL_METRICS,
  POPULARITY_BADGE_LABEL,
  type ItemDetailSuccessResponse,
} from "../../../../src/app/items/index.js";
import {
  ScaffoldApiLogger,
  type StructuredLogRecord,
} from "../../../../src/infrastructure/logger/logger.js";
import {
  registerErrorMiddleware,
  registerFoundationMiddlewares,
} from "../../../../src/middlewares/index.js";

const ACTIVE_ITEM_ID = "550e8400-e29b-41d4-a716-446655440001";
const INACTIVE_ITEM_ID = "550e8400-e29b-41d4-a716-446655440002";
const NO_IMAGE_ITEM_ID = "550e8400-e29b-41d4-a716-446655440003";

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
          {
            imageUrl: "https://example.com/images/thumb.jpg",
            imageSizeType: "small",
            displayOrder: 1,
            isPrimary: false,
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

test("GET /api/v1/items/:itemId returns 200 with contract shape", async () => {
  const logger = new ScaffoldApiLogger();
  const reader = createSeedRepository();

  await withItemsServer(
    {
      reader,
      logger,
      generatedAtFactory: () => "2026-07-15T12:00:00.000Z",
    },
    async (baseUrl) => {
      const response = await fetch(`${baseUrl}/api/v1/items/${ACTIVE_ITEM_ID}`, {
        headers: {
          Accept: "application/json",
          "X-Trace-Id": "trace-item-001",
          "X-Request-Id": "req-item-001",
        },
      });

      assert.equal(response.status, 200);
      const body = (await response.json()) as ItemDetailSuccessResponse;
      assert.equal(body.meta.traceId, "trace-item-001");
      assert.ok(body.meta.requestId);
      assert.equal(body.meta.generatedAt, "2026-07-15T12:00:00.000Z");
      assert.equal(body.data.itemId, ACTIVE_ITEM_ID);
      assert.equal(body.data.itemName, "上品な焼き菓子ギフトセット");
      assert.equal(body.data.itemPrice, 4320);
      assert.equal(body.data.isActive, true);
      assert.equal(body.data.itemImageUrl, "https://example.com/images/primary.jpg");
      assert.equal(body.data.images?.length, 2);
      assert.equal(body.data.reviewSummary?.average, 4.2);
      assert.equal(body.data.reviewSummary?.count, 128);
      assert.equal(body.data.popularityBadge?.label, POPULARITY_BADGE_LABEL);
      assert.equal(body.data.popularityBadge?.rank, 12);
      assert.equal(body.data.genreId, "100227");
      assert.equal(body.data.genreName, "スイーツ");

      const serialized = JSON.stringify(body);
      assert.equal(serialized.includes("shop_code"), false);
      assert.equal(serialized.includes("normalized_hash"), false);
      assert.equal(serialized.includes("feature"), false);
      assert.equal(serialized.includes("embedding"), false);
    },
  );

  assert.ok(
    logger.records.some(
      (record: StructuredLogRecord) =>
        record.eventName === ITEM_DETAIL_METRICS.REQUEST_COUNT &&
        record.attributes?.httpStatus === 200 &&
        record.attributes?.itemId === ACTIVE_ITEM_ID,
    ),
  );
});

test("GET /api/v1/items/:itemId returns 404 GRS-ITM-001 for unknown item", async () => {
  const logger = new ScaffoldApiLogger();
  const reader = createSeedRepository();

  await withItemsServer({ reader, logger }, async (baseUrl) => {
    const response = await fetch(
      `${baseUrl}/api/v1/items/550e8400-e29b-41d4-a716-446655440099`,
    );
    assert.equal(response.status, 404);
    const body = (await response.json()) as { error?: { code?: string } };
    assert.equal(body.error?.code, ITEM_DETAIL_ERROR_CODES.NOT_FOUND);
  });

  assert.ok(
    logger.records.some(
      (record: StructuredLogRecord) =>
        record.eventName === ITEM_DETAIL_METRICS.NOT_FOUND_COUNT,
    ),
  );
});

test("GET /api/v1/items/:itemId returns 422 GRS-ITM-002 for inactive item", async () => {
  const reader = createSeedRepository();

  await withItemsServer({ reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/items/${INACTIVE_ITEM_ID}`);
    assert.equal(response.status, 422);
    const body = (await response.json()) as { error?: { code?: string } };
    assert.equal(body.error?.code, ITEM_DETAIL_ERROR_CODES.INACTIVE);
  });
});

test("GET /api/v1/items/:itemId returns 200 without images when none exist", async () => {
  const reader = createSeedRepository();

  await withItemsServer({ reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/items/${NO_IMAGE_ITEM_ID}`);
    assert.equal(response.status, 200);
    const body = (await response.json()) as ItemDetailSuccessResponse;
    assert.equal("itemImageUrl" in body.data, false);
    assert.equal("images" in body.data, false);
    assert.equal(body.data.isActive, true);
  });
});

test("GET /api/v1/items/:itemId returns 400 GRS-REQ-001 for unknown query", async () => {
  const reader = createSeedRepository();

  await withItemsServer({ reader }, async (baseUrl) => {
    const response = await fetch(
      `${baseUrl}/api/v1/items/${ACTIVE_ITEM_ID}?foo=bar`,
    );
    assert.equal(response.status, 400);
    const body = (await response.json()) as { error?: { code?: string } };
    assert.equal(body.error?.code, ITEM_DETAIL_ERROR_CODES.INVALID_REQUEST);
  });
});

test("GET /api/v1/items/:itemId returns 400 GRS-REQ-001 for invalid itemId", async () => {
  const reader = createSeedRepository();

  await withItemsServer({ reader }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/items/item%40bad`);
    assert.equal(response.status, 400);
    const body = (await response.json()) as { error?: { code?: string } };
    assert.equal(body.error?.code, ITEM_DETAIL_ERROR_CODES.INVALID_REQUEST);
  });
});

test("createItemsRouter records item_detail_request_count on errors", async () => {
  const logger = new ScaffoldApiLogger();
  const reader = createSeedRepository();

  await withItemsServer({ reader, logger }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/items/${INACTIVE_ITEM_ID}`);
    assert.equal(response.status, 422);
  });

  const requestMetrics = logger.records.filter(
    (record: StructuredLogRecord) =>
      record.eventName === ITEM_DETAIL_METRICS.REQUEST_COUNT,
  );
  assert.equal(requestMetrics.length, 1);
  assert.equal(requestMetrics[0]?.attributes?.httpStatus, 422);
  assert.equal(
    requestMetrics[0]?.attributes?.code,
    ITEM_DETAIL_ERROR_CODES.INACTIVE,
  );
});
