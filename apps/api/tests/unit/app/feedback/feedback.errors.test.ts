import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { test } from "node:test";
import express from "express";

import {
  createFeedbackRouter,
  createFeedbackService,
  FEEDBACK_ERROR_CODES,
  FEEDBACK_ERROR_MESSAGES,
  FEEDBACK_METRICS,
  InMemoryFeedbackRepository,
  type FeedbackPersistenceInput,
  type FeedbackRecord,
  type InMemoryFeedbackStoreSeed,
} from "../../../../src/app/feedback/index.js";
import {
  ScaffoldApiLogger,
  type StructuredLogRecord,
} from "../../../../src/infrastructure/logger/logger.js";
import { ApiError } from "../../../../src/middlewares/error/api-error.js";
import {
  registerErrorMiddleware,
  registerFoundationMiddlewares,
} from "../../../../src/middlewares/index.js";

const RESULT_ID = "result-001";
const ITEM_ID = "result-item-001";
const REASON_ID = "reason-001";

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

const defaultSeed: InMemoryFeedbackStoreSeed = {
  results: [
    {
      recommendationResultId: RESULT_ID,
      recommendationRunId: "run-001",
      recommendationRequestId: "req-001",
    },
  ],
  items: [
    {
      recommendationResultItemId: ITEM_ID,
      recommendationResultId: RESULT_ID,
      itemId: "product-001",
      rank: 1,
    },
  ],
  reasons: [
    {
      recommendationReasonId: REASON_ID,
      recommendationResultId: RESULT_ID,
      recommendationResultItemId: ITEM_ID,
    },
  ],
};

function createSeedRepository(seed: InMemoryFeedbackStoreSeed = {}) {
  return new InMemoryFeedbackRepository({
    ...defaultSeed,
    ...seed,
    results: seed.results ?? defaultSeed.results,
    items: seed.items ?? defaultSeed.items,
    reasons: seed.reasons ?? defaultSeed.reasons,
  });
}

async function withFeedbackServer(
  deps: Parameters<typeof createFeedbackRouter>[0],
  run: (baseUrl: string) => Promise<void>,
): Promise<void> {
  const app = express();
  registerFoundationMiddlewares(app);
  app.use("/api/v1/recommendation-results", createFeedbackRouter(deps));
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

function feedbackUrl(baseUrl: string): string {
  return `${baseUrl}/api/v1/recommendation-results/${RESULT_ID}/feedback`;
}

const jsonHeaders = {
  "Content-Type": "application/json",
  Accept: "application/json",
} as const;

class SaveFailRepository extends InMemoryFeedbackRepository {
  override async insert(
    _input: FeedbackPersistenceInput,
  ): Promise<FeedbackRecord> {
    throw new ApiError({
      code: FEEDBACK_ERROR_CODES.SAVE_FAILED,
      httpStatus: 500,
      message: FEEDBACK_ERROR_MESSAGES.SAVE_FAILED,
      retryable: true,
    });
  }
}

test("POST feedback without sessionId twice always returns 201 accepted", async () => {
  const repository = createSeedRepository();

  await withFeedbackServer({ repository }, async (baseUrl) => {
    const url = feedbackUrl(baseUrl);
    const payload = {
      feedbackTargetType: "result",
      feedbackType: "result_good",
      rating: 5,
    };

    const first = await fetch(url, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    });
    const second = await fetch(url, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    });

    assert.equal(first.status, 201);
    assert.equal(second.status, 201);
    const firstBody = (await first.json()) as { data: { status: string } };
    const secondBody = (await second.json()) as { data: { status: string } };
    assert.equal(firstBody.data.status, "accepted");
    assert.equal(secondBody.data.status, "accepted");
    assert.equal(repository.feedbacks.length, 2);
  });
});

test("POST feedback returns 400 GRS-FDB-001 when rating missing", async () => {
  const repository = createSeedRepository();

  await withFeedbackServer({ repository }, async (baseUrl) => {
    const response = await fetch(feedbackUrl(baseUrl), {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({
        feedbackTargetType: "item",
        resultItemId: ITEM_ID,
        feedbackType: "item_good",
      }),
    });

    assert.equal(response.status, 400);
    const body = (await response.json()) as ErrorBody;
    assert.equal(body.error.code, FEEDBACK_ERROR_CODES.INVALID_CONTENT);
    assert.equal(repository.feedbacks.length, 0);
  });
});

test("POST feedback returns 400 GRS-FDB-004 when comment exceeds 500 chars", async () => {
  const repository = createSeedRepository();

  await withFeedbackServer({ repository }, async (baseUrl) => {
    const response = await fetch(feedbackUrl(baseUrl), {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({
        feedbackTargetType: "item",
        resultItemId: ITEM_ID,
        feedbackType: "item_good",
        rating: 4,
        comment: "a".repeat(501),
      }),
    });

    assert.equal(response.status, 400);
    const body = (await response.json()) as ErrorBody;
    assert.equal(body.error.code, FEEDBACK_ERROR_CODES.COMMENT_TOO_LONG);
    assert.equal(repository.feedbacks.length, 0);
  });
});

test("POST feedback returns 404 GRS-FDB-002 when item does not belong to result", async () => {
  const repository = createSeedRepository({
    items: [
      {
        recommendationResultItemId: ITEM_ID,
        recommendationResultId: "other-result",
        itemId: "product-001",
        rank: 1,
      },
    ],
  });

  await withFeedbackServer({ repository }, async (baseUrl) => {
    const response = await fetch(feedbackUrl(baseUrl), {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({
        feedbackTargetType: "item",
        resultItemId: ITEM_ID,
        feedbackType: "item_bad",
        rating: 2,
      }),
    });

    assert.equal(response.status, 404);
    const body = (await response.json()) as ErrorBody;
    assert.equal(body.error.code, FEEDBACK_ERROR_CODES.TARGET_NOT_FOUND);
  });
});

test("POST feedback returns 404 GRS-FDB-002 when reason is missing", async () => {
  const repository = createSeedRepository();

  await withFeedbackServer({ repository }, async (baseUrl) => {
    const response = await fetch(feedbackUrl(baseUrl), {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({
        feedbackTargetType: "reason",
        reasonId: "missing-reason",
        feedbackType: "reason_good",
        rating: 5,
      }),
    });

    assert.equal(response.status, 404);
    const body = (await response.json()) as ErrorBody;
    assert.equal(body.error.code, FEEDBACK_ERROR_CODES.TARGET_NOT_FOUND);
  });
});

test("SaveFailRepository returns 500 GRS-FDB-005 and records feedback_error_count", async () => {
  const logger = new ScaffoldApiLogger();
  const repository = new SaveFailRepository(defaultSeed);
  const service = createFeedbackService({ repository });

  await withFeedbackServer({ service, logger }, async (baseUrl) => {
    const response = await fetch(feedbackUrl(baseUrl), {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({
        feedbackTargetType: "item",
        resultItemId: ITEM_ID,
        feedbackType: "item_good",
        rating: 5,
      }),
    });

    assert.equal(response.status, 500);
    const body = (await response.json()) as ErrorBody;
    assert.equal(body.error.code, FEEDBACK_ERROR_CODES.SAVE_FAILED);
    assert.equal(JSON.stringify(body).includes("stack"), false);
  });

  const errorMetric = logger.records.find(
    (record: StructuredLogRecord) =>
      record.eventName === FEEDBACK_METRICS.ERROR_COUNT,
  );
  assert.ok(errorMetric);
  assert.equal(errorMetric?.attributes?.code, FEEDBACK_ERROR_CODES.SAVE_FAILED);
});

test("error response omits stack and success response omits userAgent", async () => {
  const repository = createSeedRepository();

  await withFeedbackServer({ repository }, async (baseUrl) => {
    const errorResponse = await fetch(feedbackUrl(baseUrl), {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({
        feedbackTargetType: "result",
        feedbackType: "item_good",
        rating: 4,
      }),
    });
    assert.equal(errorResponse.status, 400);
    const errorBody = (await errorResponse.json()) as ErrorBody;
    assert.equal(JSON.stringify(errorBody).includes("stack"), false);

    const successResponse = await fetch(feedbackUrl(baseUrl), {
      method: "POST",
      headers: {
        ...jsonHeaders,
        "User-Agent": "GiftRecommendTestAgent/1.0",
      },
      body: JSON.stringify({
        feedbackTargetType: "item",
        resultItemId: ITEM_ID,
        feedbackType: "item_good",
        rating: 5,
      }),
    });
    assert.equal(successResponse.status, 201);
    const successBody = (await successResponse.json()) as {
      data: Record<string, unknown>;
    };
    assert.equal("userAgent" in successBody.data, false);
    assert.equal("user_agent" in successBody.data, false);
  });
});

test("idempotent resubmit returns 200 updated without 409 or GRS-FDB-003", async () => {
  const repository = createSeedRepository();

  await withFeedbackServer({ repository }, async (baseUrl) => {
    const url = feedbackUrl(baseUrl);
    const payload = {
      feedbackTargetType: "item",
      resultItemId: ITEM_ID,
      feedbackType: "item_good",
      rating: 4,
      sessionId: "sess-idempotent",
    };

    const first = await fetch(url, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    });
    assert.equal(first.status, 201);

    const second = await fetch(url, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ ...payload, rating: 2 }),
    });

    assert.equal(second.status, 200);
    assert.notEqual(second.status, 409);
    const body = (await second.json()) as {
      data: { status: string };
      error?: { code: string };
    };
    assert.equal(body.data.status, "updated");
    assert.equal(body.error?.code, undefined);
    assert.notEqual(body.error?.code, "GRS-FDB-003");
  });
});

test("POST feedback returns 400 GRS-REQ-001 for invalid Content-Type", async () => {
  const repository = createSeedRepository();

  await withFeedbackServer({ repository }, async (baseUrl) => {
    const response = await fetch(feedbackUrl(baseUrl), {
      method: "POST",
      headers: {
        "Content-Type": "text/plain",
        Accept: "application/json",
      },
      body: JSON.stringify({
        feedbackTargetType: "item",
        resultItemId: ITEM_ID,
        feedbackType: "item_good",
        rating: 5,
      }),
    });

    assert.equal(response.status, 400);
    const body = (await response.json()) as ErrorBody;
    assert.equal(body.error.code, FEEDBACK_ERROR_CODES.INVALID_REQUEST);
  });
});

test("POST feedback returns 400 GRS-REQ-001 for invalid Accept", async () => {
  const repository = createSeedRepository();

  await withFeedbackServer({ repository }, async (baseUrl) => {
    const response = await fetch(feedbackUrl(baseUrl), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/html",
      },
      body: JSON.stringify({
        feedbackTargetType: "item",
        resultItemId: ITEM_ID,
        feedbackType: "item_good",
        rating: 5,
      }),
    });

    assert.equal(response.status, 400);
    const body = (await response.json()) as ErrorBody;
    assert.equal(body.error.code, FEEDBACK_ERROR_CODES.INVALID_REQUEST);
  });
});

test("non-POST method is not handled as success (404 or 405)", async () => {
  const repository = createSeedRepository();

  await withFeedbackServer({ repository }, async (baseUrl) => {
    const response = await fetch(feedbackUrl(baseUrl), {
      method: "GET",
      headers: { Accept: "application/json" },
    });
    assert.ok([404, 405].includes(response.status));
  });
});
