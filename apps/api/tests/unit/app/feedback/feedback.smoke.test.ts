import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { test } from "node:test";
import express from "express";

import {
  createFeedbackRouter,
  FEEDBACK_ERROR_CODES,
  FEEDBACK_METRICS,
  InMemoryFeedbackRepository,
  type FeedbackSubmitSuccessResponse,
} from "../../../../src/app/feedback/index.js";
import {
  ScaffoldApiLogger,
  type StructuredLogRecord,
} from "../../../../src/infrastructure/logger/logger.js";
import {
  registerErrorMiddleware,
  registerFoundationMiddlewares,
} from "../../../../src/middlewares/index.js";

const RESULT_ID = "result-001";
const ITEM_ID = "result-item-001";
const REASON_ID = "reason-001";

function createSeedRepository() {
  return new InMemoryFeedbackRepository({
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

test("POST feedback returns 201 accepted for new reason feedback", async () => {
  const repository = createSeedRepository();

  await withFeedbackServer({ repository }, async (baseUrl) => {
    const response = await fetch(
      `${baseUrl}/api/v1/recommendation-results/${RESULT_ID}/feedback`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          feedbackTargetType: "reason",
          reasonId: REASON_ID,
          feedbackType: "reason_good",
          rating: 5,
        }),
      },
    );

    assert.equal(response.status, 201);
    const body = (await response.json()) as FeedbackSubmitSuccessResponse;
    assert.equal(body.data.status, "accepted");
    assert.equal(repository.feedbacks.length, 1);
  });
});

test("POST feedback returns 201 accepted for new result feedback", async () => {
  const repository = createSeedRepository();

  await withFeedbackServer({ repository }, async (baseUrl) => {
    const response = await fetch(
      `${baseUrl}/api/v1/recommendation-results/${RESULT_ID}/feedback`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          feedbackTargetType: "result",
          feedbackType: "result_good",
          rating: 4,
        }),
      },
    );

    assert.equal(response.status, 201);
    const body = (await response.json()) as FeedbackSubmitSuccessResponse;
    assert.equal(body.data.status, "accepted");
    assert.equal(repository.feedbacks.length, 1);
  });
});

test("POST feedback returns 201 accepted for new item feedback", async () => {
  const repository = createSeedRepository();

  await withFeedbackServer({ repository }, async (baseUrl) => {
    const response = await fetch(
      `${baseUrl}/api/v1/recommendation-results/${RESULT_ID}/feedback`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-Trace-Id": "trace-fdb-001",
        },
        body: JSON.stringify({
          feedbackTargetType: "item",
          resultItemId: ITEM_ID,
          feedbackType: "item_good",
          rating: 5,
          sessionId: "sess-new",
        }),
      },
    );

    assert.equal(response.status, 201);
    const body = (await response.json()) as FeedbackSubmitSuccessResponse;
    assert.equal(body.data.status, "accepted");
    assert.equal(body.meta.traceId, "trace-fdb-001");
    assert.ok(body.meta.acceptedAt);
    assert.equal("sessionId" in body.data, false);
    assert.equal("userAgent" in body.data, false);
    assert.equal(repository.feedbacks.length, 1);
  });
});

test("POST feedback returns 200 updated for idempotent resubmit", async () => {
  const repository = createSeedRepository();

  await withFeedbackServer({ repository }, async (baseUrl) => {
    const url = `${baseUrl}/api/v1/recommendation-results/${RESULT_ID}/feedback`;
    const payload = {
      feedbackTargetType: "item",
      resultItemId: ITEM_ID,
      feedbackType: "item_good",
      rating: 4,
      sessionId: "sess-dup",
    };

    const first = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });
    assert.equal(first.status, 201);
    const firstBody = (await first.json()) as FeedbackSubmitSuccessResponse;

    const second = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ ...payload, rating: 2 }),
    });
    assert.equal(second.status, 200);
    const secondBody = (await second.json()) as FeedbackSubmitSuccessResponse;
    assert.equal(secondBody.data.status, "updated");
    assert.equal(
      secondBody.data.recommendationFeedbackId,
      firstBody.data.recommendationFeedbackId,
    );
  });
});

test("POST feedback returns 400 GRS-FDB-001 for invalid type/target pair", async () => {
  const repository = createSeedRepository();

  await withFeedbackServer({ repository }, async (baseUrl) => {
    const response = await fetch(
      `${baseUrl}/api/v1/recommendation-results/${RESULT_ID}/feedback`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          feedbackTargetType: "result",
          feedbackType: "item_good",
          rating: 4,
        }),
      },
    );

    assert.equal(response.status, 400);
    const body = (await response.json()) as { error?: { code?: string } };
    assert.equal(body.error?.code, FEEDBACK_ERROR_CODES.INVALID_CONTENT);
    assert.equal(repository.feedbacks.length, 0);
  });
});

test("POST feedback returns 404 GRS-FDB-002 for missing result", async () => {
  const repository = createSeedRepository();

  await withFeedbackServer({ repository }, async (baseUrl) => {
    const response = await fetch(
      `${baseUrl}/api/v1/recommendation-results/missing-result/feedback`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          feedbackTargetType: "result",
          feedbackType: "result_good",
          rating: 4,
        }),
      },
    );

    assert.equal(response.status, 404);
    const body = (await response.json()) as { error?: { code?: string } };
    assert.equal(body.error?.code, FEEDBACK_ERROR_CODES.TARGET_NOT_FOUND);
  });
});

test("createFeedbackRouter records feedback metrics via logger", async () => {
  const logger = new ScaffoldApiLogger();
  const repository = createSeedRepository();

  await withFeedbackServer({ repository, logger }, async (baseUrl) => {
    const response = await fetch(
      `${baseUrl}/api/v1/recommendation-results/${RESULT_ID}/feedback`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          feedbackTargetType: "item",
          resultItemId: ITEM_ID,
          feedbackType: "item_bad",
          rating: 2,
        }),
      },
    );
    assert.equal(response.status, 201);
  });

  const countMetric = logger.records.find(
    (record: StructuredLogRecord) => record.eventName === FEEDBACK_METRICS.COUNT,
  );
  assert.ok(countMetric);
  assert.equal(countMetric?.attributes?.httpStatus, 201);

  const negativeMetric = logger.records.find(
    (record: StructuredLogRecord) =>
      record.eventName === FEEDBACK_METRICS.NEGATIVE_COUNT,
  );
  assert.ok(negativeMetric);
});

test("createFeedbackRouter records positive_feedback_count for item_good", async () => {
  const logger = new ScaffoldApiLogger();
  const repository = createSeedRepository();

  await withFeedbackServer({ repository, logger }, async (baseUrl) => {
    const response = await fetch(
      `${baseUrl}/api/v1/recommendation-results/${RESULT_ID}/feedback`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          feedbackTargetType: "item",
          resultItemId: ITEM_ID,
          feedbackType: "item_good",
          rating: 5,
        }),
      },
    );
    assert.equal(response.status, 201);
  });

  const positiveMetric = logger.records.find(
    (record: StructuredLogRecord) =>
      record.eventName === FEEDBACK_METRICS.POSITIVE_COUNT,
  );
  assert.ok(positiveMetric);
  assert.equal(positiveMetric?.attributes?.httpStatus, 201);
});
