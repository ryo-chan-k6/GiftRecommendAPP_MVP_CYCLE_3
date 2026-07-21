import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiError } from "../../../../src/middlewares/error/api-error.js";
import {
  createFeedbackService,
  FEEDBACK_ERROR_CODES,
  InMemoryFeedbackRepository,
  validateFeedbackSubmitRequest,
  type InMemoryFeedbackStoreSeed,
} from "../../../../src/app/feedback/index.js";

const RESULT_ID = "result-001";
const ITEM_ID = "result-item-001";
const REASON_ID = "reason-001";
const SESSION_ID = "sess-abc";

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

function createTestService(seed: InMemoryFeedbackStoreSeed = {}) {
  const repository = new InMemoryFeedbackRepository({
    ...defaultSeed,
    ...seed,
    results: seed.results ?? defaultSeed.results,
    items: seed.items ?? defaultSeed.items,
    reasons: seed.reasons ?? defaultSeed.reasons,
  });

  return {
    repository,
    service: createFeedbackService({ repository }),
  };
}

test("FeedbackService inserts new feedback with 201 accepted when sessionId absent", async () => {
  const { repository, service } = createTestService();

  const result = await service.submitFeedback({
    resultId: RESULT_ID,
    request: validateFeedbackSubmitRequest({
      feedbackTargetType: "item",
      resultItemId: ITEM_ID,
      feedbackType: "item_good",
      rating: 5,
    }),
    traceId: "trace-1",
    requestId: "request-1",
  });

  assert.equal(result.httpStatus, 201);
  assert.equal(result.body.data.status, "accepted");
  assert.equal(result.isPositive, true);
  assert.equal(result.isNegative, false);
  assert.equal(repository.feedbacks.length, 1);
});

test("FeedbackService updates existing feedback with 200 updated for idempotent key", async () => {
  const { repository, service } = createTestService();

  const request = validateFeedbackSubmitRequest({
    feedbackTargetType: "item",
    resultItemId: ITEM_ID,
    feedbackType: "item_good",
    rating: 4,
    sessionId: SESSION_ID,
  });

  const first = await service.submitFeedback({
    resultId: RESULT_ID,
    request,
    traceId: "trace-1",
    requestId: "request-1",
  });
  assert.equal(first.httpStatus, 201);

  const second = await service.submitFeedback({
    resultId: RESULT_ID,
    request: validateFeedbackSubmitRequest({
      ...request,
      rating: 2,
      comment: "updated comment",
    }),
    traceId: "trace-2",
    requestId: "request-2",
  });

  assert.equal(second.httpStatus, 200);
  assert.equal(second.body.data.status, "updated");
  assert.equal(second.body.data.recommendationFeedbackId, first.body.data.recommendationFeedbackId);
  assert.equal(repository.feedbacks.length, 1);
  assert.equal(repository.feedbacks[0]?.feedbackRating, 2);
  assert.equal(repository.feedbacks[0]?.feedbackText, "updated comment");
});

test("FeedbackService always inserts when sessionId absent even on resubmit", async () => {
  const { repository, service } = createTestService();
  const request = validateFeedbackSubmitRequest({
    feedbackTargetType: "result",
    feedbackType: "result_good",
    rating: 5,
  });

  await service.submitFeedback({
    resultId: RESULT_ID,
    request,
    traceId: "trace-1",
    requestId: "request-1",
  });
  const second = await service.submitFeedback({
    resultId: RESULT_ID,
    request,
    traceId: "trace-2",
    requestId: "request-2",
  });

  assert.equal(second.httpStatus, 201);
  assert.equal(repository.feedbacks.length, 2);
});

test("FeedbackService returns 404 GRS-FDB-002 when result missing", async () => {
  const { service } = createTestService();

  await assert.rejects(
    () =>
      service.submitFeedback({
        resultId: "missing-result",
        request: validateFeedbackSubmitRequest({
          feedbackTargetType: "result",
          feedbackType: "result_good",
          rating: 4,
        }),
        traceId: "trace-1",
        requestId: "request-1",
      }),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.code, FEEDBACK_ERROR_CODES.TARGET_NOT_FOUND);
      assert.equal(error.httpStatus, 404);
      return true;
    },
  );
});

test("FeedbackService returns 404 when item does not belong to result", async () => {
  const { service } = createTestService({
    items: [
      {
        recommendationResultItemId: ITEM_ID,
        recommendationResultId: "other-result",
        itemId: "product-001",
        rank: 1,
      },
    ],
  });

  await assert.rejects(
    () =>
      service.submitFeedback({
        resultId: RESULT_ID,
        request: validateFeedbackSubmitRequest({
          feedbackTargetType: "item",
          resultItemId: ITEM_ID,
          feedbackType: "item_bad",
          rating: 2,
        }),
        traceId: "trace-1",
        requestId: "request-1",
      }),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.code, FEEDBACK_ERROR_CODES.TARGET_NOT_FOUND);
      return true;
    },
  );
});

test("FeedbackService handles unique race by retrying update to 200", async () => {
  class RaceSimulatingRepository extends InMemoryFeedbackRepository {
    private findCalls = 0;

    override async findByIdempotencyKey(
      lookup: import("../../../../src/app/feedback/types.js").IdempotencyLookup,
    ) {
      this.findCalls += 1;
      if (this.findCalls === 1) {
        return null;
      }
      return super.findByIdempotencyKey(lookup);
    }
  }

  const repository = new RaceSimulatingRepository({
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
  });

  const service = createFeedbackService({ repository });
  const request = validateFeedbackSubmitRequest({
    feedbackTargetType: "item",
    resultItemId: ITEM_ID,
    feedbackType: "item_not_match",
    rating: 1,
    sessionId: SESSION_ID,
  });

  await repository.insert({
    recommendationResultId: RESULT_ID,
    recommendationRunId: "run-001",
    recommendationRequestId: "req-001",
    recommendationResultItemId: ITEM_ID,
    recommendationReasonId: null,
    feedbackTargetType: "item",
    feedbackType: "item_not_match",
    feedbackValueType: "choice",
    feedbackValue: null,
    feedbackChoiceCode: null,
    feedbackReasonCategory: null,
    feedbackRating: 1,
    feedbackText: null,
    sourcePage: null,
    sessionId: SESSION_ID,
    userAgent: null,
    itemId: "product-001",
    rankAtFeedback: 1,
    isPositive: false,
    isNegative: true,
  });

  const result = await service.submitFeedback({
    resultId: RESULT_ID,
    request,
    traceId: "trace-race",
    requestId: "request-race",
  });

  assert.equal(result.httpStatus, 200);
  assert.equal(result.body.data.status, "updated");
  assert.equal(repository.feedbacks.length, 1);
});

test("FeedbackService response meta includes traceId and requestId", async () => {
  const { service } = createTestService();

  const result = await service.submitFeedback({
    resultId: RESULT_ID,
    request: validateFeedbackSubmitRequest({
      feedbackTargetType: "reason",
      reasonId: REASON_ID,
      feedbackType: "reason_good",
      rating: 5,
    }),
    traceId: "trace-meta",
    requestId: "request-meta",
  });

  assert.equal(result.body.meta.traceId, "trace-meta");
  assert.equal(result.body.meta.requestId, "request-meta");
  assert.ok(result.body.meta.acceptedAt);
});
