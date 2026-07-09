import { test } from "node:test";
import assert from "node:assert/strict";

import { ApiError } from "../../../../src/middlewares/error/api-error.js";
import { isRecoError, RecoError } from "../../../../src/infrastructure/reco-client/errors.js";
import {
  mapRecoErrorToApiError,
  mapRecoResultToPublicResponse,
  PUBLIC_ERROR_CODES,
  validateRecommendationRunRequest,
} from "../../../../src/app/recommendations/index.js";

const validRequestBody = {
  relationship: { relationshipCode: "boss" },
  occasion: { occasionCode: "thanks" },
  execution: { mode: "ui" },
};

test("validateRecommendationRunRequest returns normalized request with defaults", () => {
  const result = validateRecommendationRunRequest(validRequestBody);

  assert.equal(result.relationship.relationshipCode, "boss");
  assert.equal(result.execution.mode, "ui");
  assert.equal(result.execution.topK, 10);
  assert.equal(result.execution.candidateLimit, 50);
  assert.equal(result.execution.includeReason, true);
  assert.equal(result.execution.includeDebugInfo, false);
});

test("validateRecommendationRunRequest throws GRS-REQ-004 when relationship missing", () => {
  assert.throws(
    () =>
      validateRecommendationRunRequest({
        relationship: { relationshipCode: "" },
        occasion: { occasionCode: "thanks" },
        execution: { mode: "ui" },
      }),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      const apiError = error as ApiError;
      assert.equal(apiError.code, PUBLIC_ERROR_CODES.RELATIONSHIP_REQUIRED);
      assert.equal(apiError.httpStatus, 400);
      return true;
    },
  );
});

test("validateRecommendationRunRequest throws GRS-REQ-005 when occasion missing", () => {
  assert.throws(
    () =>
      validateRecommendationRunRequest({
        relationship: { relationshipCode: "boss" },
        occasion: { occasionCode: "  " },
        execution: { mode: "ui" },
      }),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal((error as ApiError).code, PUBLIC_ERROR_CODES.OCCASION_REQUIRED);
      return true;
    },
  );
});

test("mapRecoResultToPublicResponse maps empty completed result to empty + GRS-REC-001", () => {
  const response = mapRecoResultToPublicResponse({
    recoResult: {
      recommendationRunId: "run-1",
      recommendationResultId: "result-1",
      recommendationRequestId: "req-1",
      items: [],
      resultStatus: "completed",
      resultItemCount: 0,
    },
    recommendationRequestId: "req-1",
    traceId: "trace-1",
    requestId: "request-1",
    topK: 10,
  });

  assert.equal(response.data.resultStatus, "empty");
  assert.equal(response.data.resultItemCount, 0);
  assert.deepEqual(response.data.items, []);
  assert.equal(response.meta.resultCode, PUBLIC_ERROR_CODES.NO_CANDIDATES);
  assert.match(response.data.displayMessage ?? "", /条件に合う商品が見つかりませんでした/);
});

test("mapRecoResultToPublicResponse excludes internal score fields from items", () => {
  const response = mapRecoResultToPublicResponse({
    recoResult: {
      recommendationRunId: "run-1",
      recommendationResultId: "result-1",
      recommendationRequestId: "req-1",
      resultItemCount: 1,
      items: [
        {
          recommendationResultItemId: "item-result-1",
          itemId: "item-1",
          rank: 1,
          itemName: "Gift",
          itemPrice: 1000,
          itemUrl: "https://example.com/item/1",
          finalScore: 0.9,
          contextScore: 0.8,
          scoreBreakdown: { matching: 0.7 },
          reasonSummary: "理由",
          isFallback: false,
        },
      ],
    },
    recommendationRequestId: "req-1",
    traceId: "trace-1",
    requestId: "request-1",
    topK: 10,
  });

  assert.equal(response.data.items.length, 1);
  const item = response.data.items[0];
  assert.equal(item.reasonSummary, "理由");
  assert.equal("finalScore" in item, false);
  assert.equal("contextScore" in item, false);
  assert.equal("scoreBreakdown" in item, false);
});

test("mapRecoErrorToApiError maps reco auth failure to Public 500 GRS-REC-002", () => {
  const apiError = mapRecoErrorToApiError(
    new RecoError({
      code: "RECO_REQUEST_FAILED",
      message: "unauthorized",
      retryable: false,
      statusCode: 401,
      upstreamCode: "GRS-AUTH-001",
    }),
  );

  assert.ok(apiError instanceof ApiError);
  assert.equal(apiError.code, PUBLIC_ERROR_CODES.RECOMMENDATION_FAILED);
  assert.equal(apiError.httpStatus, 500);
});

test("mapRecoErrorToApiError maps transport failure to 502 GRS-REC-002", () => {
  const apiError = mapRecoErrorToApiError(
    new RecoError({
      code: "RECO_UNAVAILABLE",
      message: "reco service is unavailable",
      retryable: true,
      statusCode: 503,
    }),
  );

  assert.equal(apiError.httpStatus, 502);
  assert.equal(apiError.code, PUBLIC_ERROR_CODES.RECOMMENDATION_FAILED);
});

test("mapRecoErrorToApiError maps GRS-REC-101 to 504", () => {
  const apiError = mapRecoErrorToApiError(
    new RecoError({
      code: "RECO_UNAVAILABLE",
      message: "timeout",
      retryable: true,
      statusCode: 504,
      upstreamCode: PUBLIC_ERROR_CODES.RECO_TIMEOUT,
    }),
  );

  assert.equal(apiError.httpStatus, 504);
  assert.equal(apiError.code, PUBLIC_ERROR_CODES.RECO_TIMEOUT);
});

test("RecommendationApplicationService calls createRecoClient path via scaffold", async () => {
  const { RecommendationApplicationService } = await import(
    "../../../../src/app/recommendations/application-service.js"
  );
  const { RecommendationRequestRepository } = await import(
    "../../../../src/app/recommendations/request-repository.js"
  );
  const { ScaffoldDbSession } = await import(
    "../../../../src/infrastructure/db/session.js"
  );
  const { ScaffoldRecoClient } = await import(
    "../../../../src/infrastructure/reco-client/client.js"
  );

  const recoClient = new ScaffoldRecoClient({
    runResult: {
      recommendationRunId: "run-1",
      recommendationResultId: "result-1",
      recommendationRequestId: "ignored",
      resultItemCount: 1,
      items: [
        {
          recommendationResultItemId: "item-result-1",
          itemId: "item-1",
          rank: 1,
          itemName: "Gift",
          itemPrice: 1000,
          itemUrl: "https://example.com/item/1",
          finalScore: 0.9,
        },
      ],
    },
  });

  const service = new RecommendationApplicationService({
    recoClient,
    requestRepository: new RecommendationRequestRepository({
      session: new ScaffoldDbSession(),
    }),
  });

  const response = await service.runRecommendation({
    request: validateRecommendationRunRequest(validRequestBody),
    traceId: "trace-1",
    requestId: "request-1",
  });

  assert.equal(recoClient.runRecommendationCalls.length, 1);
  assert.equal(response.data.items.length, 1);
  assert.equal(response.data.resultStatus, "completed");
  assert.equal(isRecoError(undefined), false);
});
